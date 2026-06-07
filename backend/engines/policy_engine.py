"""
Deterministic policy rule engine — no LLM.
Applies all rules from policy_terms.json: waiting periods, limits,
copay, network discounts, pre-auth, exclusions, line-item decisions.
"""
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional
from models.claim import ClaimCategory, ClaimSubmission
from models.decision import (
    ClaimDecision, Decision, FinancialBreakdown,
    LineItemDecision, RejectionReason,
)
from models.trace import TraceEvent, TraceLog, CheckResult
from agents.document_parser import ParsedDocument
from config import POLICY

_EXCLUDED_KEYWORDS = [
    "whitening", "bleach", "veneer", "orthodontic", "brace", "implant",
    "lasik", "refractive", "cosmetic", "bariatric", "obesity", "weight loss",
    "infertility", "ivf", "self-inflict", "substance abuse", "experimental",
    "tonic", "supplement", "vaccination",
]

_DIABETES_KEYWORDS = ["diabetes", "diabetic", "t2dm", "type 2 diabetes", "hyperglycemia", "metformin", "glimepiride", "insulin"]
_HYPERTENSION_KEYWORDS = ["hypertension", "htn", "high blood pressure", "amlodipine", "telmisartan", "losartan"]
_THYROID_KEYWORDS = ["thyroid", "hypothyroid", "hyperthyroid", "thyroxine", "levothyroxine"]
_JOINT_REPLACEMENT_KEYWORDS = ["joint replacement", "knee replacement", "hip replacement"]
_MATERNITY_KEYWORDS = ["maternity", "pregnancy", "antenatal", "prenatal", "delivery", "obstetric"]
_MENTAL_HEALTH_KEYWORDS = ["mental health", "depression", "anxiety", "psychiatry", "psychiatric"]
_OBESITY_KEYWORDS = ["obesity", "obese", "bariatric", "weight loss", "bmi"]
_HERNIA_KEYWORDS = ["hernia", "herniation"]
_CATARACT_KEYWORDS = ["cataract"]

_PRE_AUTH_TESTS = ["mri", "ct scan", "ct-scan", "pet scan", "pet-scan"]


def _text_contains(text: str, keywords: list[str]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _get_diagnosis_text(parsed_docs: list[ParsedDocument]) -> str:
    """Returns diagnosis/treatment/medicine text only — excludes line item descriptions.
    Line items are evaluated separately in _line_item_decisions."""
    parts = []
    for doc in parsed_docs:
        parts.append(doc.data.get("diagnosis", ""))
        parts.append(doc.data.get("treatment", ""))
        parts.extend(doc.data.get("medicines", []))
        parts.extend(doc.data.get("tests_ordered", []))
    return " ".join(str(p) for p in parts if p)


def _check_waiting_period(
    member: dict,
    treatment_date_str: str,
    diagnosis_text: str,
) -> tuple[bool, str, str | None]:
    """Returns (passed, reason, eligible_from_date_str)."""
    join_date = date.fromisoformat(member["join_date"])
    treatment_date = date.fromisoformat(treatment_date_str)
    days_since_join = (treatment_date - join_date).days

    wp = POLICY["waiting_periods"]
    initial_wp = wp["initial_waiting_period_days"]
    if days_since_join < initial_wp:
        eligible = join_date + timedelta(days=initial_wp)
        return False, f"Initial waiting period of {initial_wp} days not met. Member joined {join_date}, treatment on {treatment_date}. Eligible from {eligible}.", str(eligible)

    # Condition-specific waiting periods
    specific = wp.get("specific_conditions", {})
    condition_map = [
        (_DIABETES_KEYWORDS, "diabetes", specific.get("diabetes", 90)),
        (_HYPERTENSION_KEYWORDS, "hypertension", specific.get("hypertension", 90)),
        (_THYROID_KEYWORDS, "thyroid_disorders", specific.get("thyroid_disorders", 90)),
        (_JOINT_REPLACEMENT_KEYWORDS, "joint_replacement", specific.get("joint_replacement", 730)),
        (_MATERNITY_KEYWORDS, "maternity", specific.get("maternity", 270)),
        (_MENTAL_HEALTH_KEYWORDS, "mental_health", specific.get("mental_health", 180)),
        (_OBESITY_KEYWORDS, "obesity_treatment", specific.get("obesity_treatment", 365)),
        (_HERNIA_KEYWORDS, "hernia", specific.get("hernia", 365)),
        (_CATARACT_KEYWORDS, "cataract", specific.get("cataract", 365)),
    ]
    for keywords, condition_name, wait_days in condition_map:
        if _text_contains(diagnosis_text, keywords):
            if days_since_join < wait_days:
                eligible = join_date + timedelta(days=wait_days)
                return (
                    False,
                    f"Waiting period for {condition_name} is {wait_days} days. "
                    f"Member joined {join_date} ({days_since_join} days elapsed). "
                    f"Eligible from {eligible}.",
                    str(eligible),
                )
    return True, "All waiting periods satisfied.", None


def _check_exclusions(diagnosis_text: str) -> list[str]:
    # Only check diagnosis/treatment text for whole-claim exclusions.
    # Line-item exclusions (e.g. teeth whitening) are handled in _line_item_decisions.
    excluded: list[str] = []
    for kw in _EXCLUDED_KEYWORDS:
        if kw in diagnosis_text.lower():
            excluded.append(kw)
    return excluded


def _check_pre_auth(
    category: ClaimCategory,
    claimed_amount: float,
    diagnosis_text: str,
) -> tuple[bool, str]:
    if category != ClaimCategory.DIAGNOSTIC:
        return True, "Pre-authorization not required for this category."
    pre_auth_threshold = POLICY["opd_categories"]["diagnostic"].get("pre_auth_threshold", 10000)
    high_value_tests = [t.lower() for t in POLICY["opd_categories"]["diagnostic"].get("high_value_tests_requiring_pre_auth", [])]
    needs_pre_auth = False
    for test in high_value_tests:
        if _text_contains(diagnosis_text, [test]) and claimed_amount > pre_auth_threshold:
            needs_pre_auth = True
            break
    if needs_pre_auth:
        return (
            False,
            f"Pre-authorization is required for {', '.join(high_value_tests)} when the claim amount exceeds ₹{pre_auth_threshold:,.0f}. "
            f"Please obtain pre-authorization from Plum before undergoing the procedure and resubmit.",
        )
    return True, "Pre-authorization not required."


_AGGREGATION_PREFIXES = ("subtotal", "sub total", "sub-total", "grand total", "round off", "rounding")
_AGGREGATION_EXACT = {"total", "discount", "tax", "gst", "cgst", "sgst", "igst"}


def _is_aggregation_row(desc: str) -> bool:
    """Returns True if this is a derived/aggregation row, not a billable service."""
    d = desc.lower().strip()
    if d in _AGGREGATION_EXACT:
        return True
    if any(d.startswith(p) for p in _AGGREGATION_PREFIXES):
        return True
    # "Discount (X%)", "GST @18%", etc.
    if d.startswith("discount") or d.startswith("gst") or d.startswith("tax"):
        return True
    return False


def _line_item_decisions(
    category: ClaimCategory,
    line_items: list[dict],
    diagnosis_text: str,
) -> tuple[list[LineItemDecision], float]:
    decisions: list[LineItemDecision] = []
    total_approved = 0.0

    covered_dental = [p.lower() for p in POLICY["opd_categories"]["dental"].get("covered_procedures", [])]
    excluded_dental = [p.lower() for p in POLICY["opd_categories"]["dental"].get("excluded_procedures", [])]
    covered_vision = [i.lower() for i in POLICY["opd_categories"]["vision"].get("covered_items", [])]
    excluded_vision = [i.lower() for i in POLICY["opd_categories"]["vision"].get("excluded_items", [])]

    for item in line_items:
        desc = item.get("description", "")
        amount = float(item.get("amount", 0))
        desc_lower = desc.lower()

        # Skip aggregation rows entirely — these are derived values on the bill
        # (subtotals, totals, discounts, taxes) and must not be double-counted.
        if _is_aggregation_row(desc):
            continue

        approved = True
        reason = None

        if category == ClaimCategory.DENTAL:
            if any(ex in desc_lower for ex in excluded_dental):
                approved = False
                reason = f"'{desc}' is a cosmetic dental procedure and is excluded under the policy."
            elif not any(cov in desc_lower for cov in covered_dental):
                if any(kw in desc_lower for kw in _EXCLUDED_KEYWORDS):
                    approved = False
                    reason = f"'{desc}' is excluded under the policy."
        elif category == ClaimCategory.VISION:
            if any(ex in desc_lower for ex in excluded_vision):
                approved = False
                reason = f"'{desc}' is excluded under the vision benefit (e.g., LASIK is not covered)."
        else:
            if any(kw in desc_lower for kw in _EXCLUDED_KEYWORDS):
                approved = False
                reason = f"'{desc}' is excluded under the policy."

        approved_amount = amount if approved else 0.0
        total_approved += approved_amount
        decisions.append(LineItemDecision(
            description=desc,
            amount=amount,
            approved=approved,
            approved_amount=approved_amount,
            reason=reason,
        ))

    return decisions, total_approved


def _get_member(member_id: str) -> Optional[dict]:
    for m in POLICY.get("members", []):
        if m["member_id"] == member_id:
            return m
    return None


def _is_network_hospital(hospital_name: str | None) -> bool:
    if not hospital_name:
        return False
    hn = hospital_name.lower()
    return any(hn in n.lower() or n.lower() in hn for n in POLICY.get("network_hospitals", []))


def run_policy_checks(
    submission: ClaimSubmission,
    parsed_docs: list[ParsedDocument],
    trace: TraceLog,
) -> ClaimDecision:
    checks: list[CheckResult] = []
    rejection_reasons: list[str] = []
    eligible_from_date: Optional[str] = None

    # --- Member lookup ---
    member = _get_member(submission.member_id)
    if not member:
        trace.add_event(TraceEvent(
            step=0,
            agent="PolicyEngine",
            status="FAILED",
            input_summary=f"member_id={submission.member_id}",
            output_summary="Member not found",
            checks=[CheckResult(name="member_lookup", passed=False, detail="Member ID not in roster")],
            confidence_delta=-0.5,
        ))
        return ClaimDecision(
            decision=Decision.REJECTED,
            reason=f"Member '{submission.member_id}' not found in policy roster.",
            rejection_reasons=[RejectionReason.MEMBER_NOT_FOUND.value],
            confidence_score=0.95,
        )
    checks.append(CheckResult(name="member_lookup", passed=True, detail=f"Member '{member['name']}' found"))

    diagnosis_text = _get_diagnosis_text(parsed_docs)
    category = submission.claim_category
    cat_config = POLICY["opd_categories"].get(category.value.lower(), {})

    # --- Waiting period ---
    wp_ok, wp_reason, eligible_date = _check_waiting_period(
        member, submission.treatment_date, diagnosis_text
    )
    checks.append(CheckResult(name="waiting_period", passed=wp_ok, detail=wp_reason))
    if not wp_ok:
        eligible_from_date = eligible_date
        rejection_reasons.append(RejectionReason.WAITING_PERIOD.value)

    # --- Exclusions check ---
    exclusion_hits = _check_exclusions(diagnosis_text)
    excl_ok = len(exclusion_hits) == 0
    checks.append(CheckResult(
        name="exclusions",
        passed=excl_ok,
        detail=f"Excluded keywords found: {exclusion_hits}" if not excl_ok else "No excluded conditions detected",
    ))
    if not excl_ok:
        rejection_reasons.append(RejectionReason.EXCLUDED_CONDITION.value)

    # --- Pre-authorization check ---
    pre_auth_ok, pre_auth_reason = _check_pre_auth(category, submission.claimed_amount, diagnosis_text)
    checks.append(CheckResult(name="pre_authorization", passed=pre_auth_ok, detail=pre_auth_reason))
    if not pre_auth_ok:
        rejection_reasons.append(RejectionReason.PRE_AUTH_MISSING.value)

    # --- Per-claim limit (OPD categories only) ---
    # DENTAL, VISION, ALTERNATIVE_MEDICINE have their own higher sub-limits;
    # the global per_claim_limit only hard-rejects OPD categories.
    per_claim_limit = POLICY["coverage"]["per_claim_limit"]
    _opd_categories = {ClaimCategory.CONSULTATION, ClaimCategory.PHARMACY, ClaimCategory.DIAGNOSTIC}
    if category in _opd_categories:
        per_claim_ok = submission.claimed_amount <= per_claim_limit
        checks.append(CheckResult(
            name="per_claim_limit",
            passed=per_claim_ok,
            detail=f"Claimed ₹{submission.claimed_amount:,.0f} vs limit ₹{per_claim_limit:,.0f}",
        ))
        if not per_claim_ok:
            rejection_reasons.append(RejectionReason.PER_CLAIM_EXCEEDED.value)
    else:
        checks.append(CheckResult(
            name="per_claim_limit",
            passed=True,
            detail=f"Per-claim limit not applied to {category.value} (governed by sub-limit)",
        ))

    # Sub-limit: informational only — used as financial cap, not hard rejection
    sub_limit = cat_config.get("sub_limit")

    # --- Annual OPD limit ---
    annual_limit = POLICY["coverage"]["annual_opd_limit"]
    ytd = submission.ytd_claims_amount
    annual_ok = (ytd + submission.claimed_amount) <= annual_limit
    checks.append(CheckResult(
        name="annual_limit",
        passed=annual_ok,
        detail=f"YTD ₹{ytd:,.0f} + claimed ₹{submission.claimed_amount:,.0f} vs annual ₹{annual_limit:,.0f}",
    ))
    if not annual_ok:
        rejection_reasons.append(RejectionReason.ANNUAL_LIMIT_EXCEEDED.value)

    # --- If hard rejections exist, return REJECTED ---
    hard_reject_reasons = [RejectionReason.WAITING_PERIOD.value, RejectionReason.PRE_AUTH_MISSING.value,
                           RejectionReason.PER_CLAIM_EXCEEDED.value, RejectionReason.EXCLUDED_CONDITION.value,
                           RejectionReason.ANNUAL_LIMIT_EXCEEDED.value, RejectionReason.MEMBER_NOT_FOUND.value,
                           RejectionReason.SUB_LIMIT_EXCEEDED.value]
    has_hard_rejection = any(r in hard_reject_reasons for r in rejection_reasons)

    if has_hard_rejection:
        reasons_text = _build_rejection_text(rejection_reasons, submission, per_claim_limit, eligible_from_date)
        trace.add_event(TraceEvent(
            step=0,
            agent="PolicyEngine",
            status="FAILED",
            input_summary=f"member={member['name']}, category={category.value}, amount=₹{submission.claimed_amount:,.0f}",
            output_summary=f"REJECTED: {rejection_reasons}",
            checks=checks,
            confidence_delta=-0.05,
        ))
        return ClaimDecision(
            decision=Decision.REJECTED,
            reason=reasons_text,
            rejection_reasons=rejection_reasons,
            confidence_score=0.95,
            eligible_from_date=eligible_from_date,
        )

    # --- Financial calculation ---
    # Line-item decisions (for partial approvals).
    # Aggregation rows (subtotal, total, discount, tax) are filtered inside
    # _line_item_decisions so they are never double-counted.
    all_line_items = [item for doc in parsed_docs for item in doc.line_items]
    if all_line_items:
        line_decisions, items_approved_total = _line_item_decisions(category, all_line_items, diagnosis_text)
        # Use document-extracted total but never exceed what the member actually claimed.
        base_amount = min(items_approved_total, submission.claimed_amount)
    else:
        line_decisions = []
        base_amount = submission.claimed_amount

    # Cap at sub-limit (non-OPD categories); OPD categories already passed per-claim check
    if sub_limit and category not in _opd_categories:
        base_amount = min(base_amount, sub_limit)

    # Network discount (applied BEFORE copay)
    hospital_name = submission.hospital_name or next(
        (doc.hospital_name for doc in parsed_docs if doc.hospital_name), None
    )
    is_network = _is_network_hospital(hospital_name)
    network_discount_pct = cat_config.get("network_discount_percent", 0) / 100 if is_network else 0.0
    discount_amount = round(base_amount * network_discount_pct, 2)
    amount_after_discount = round(base_amount - discount_amount, 2)

    checks.append(CheckResult(
        name="network_hospital",
        passed=True,
        detail=f"{'Network hospital detected' if is_network else 'Non-network hospital'}. Discount: {network_discount_pct * 100:.0f}%",
    ))

    # Co-pay (applied AFTER network discount)
    copay_pct = cat_config.get("copay_percent", 0) / 100
    copay_amount = round(amount_after_discount * copay_pct, 2)
    final_approved = round(amount_after_discount - copay_amount, 2)

    checks.append(CheckResult(
        name="copay",
        passed=True,
        detail=f"Co-pay {copay_pct * 100:.0f}% = ₹{copay_amount:,.2f}. Final approved: ₹{final_approved:,.2f}",
    ))

    # Always assert the invariant: approved ≤ claimed.
    # (Floating point edge cases or rounding must not breach this.)
    final_approved = min(final_approved, submission.claimed_amount)

    breakdown = FinancialBreakdown(
        claimed_amount=base_amount,          # actual calculation base (line items or claimed, whichever is lower)
        network_discount_amount=discount_amount,
        amount_after_discount=amount_after_discount,
        copay_amount=copay_amount,
        approved_amount=final_approved,
        sub_limit_cap=sub_limit,
        per_claim_cap=per_claim_limit,
    )

    # Determine APPROVED vs PARTIAL
    has_excluded_items = any(not d.approved for d in line_decisions)
    decision = Decision.PARTIAL if has_excluded_items else Decision.APPROVED

    reason = _build_approval_text(decision, breakdown, line_decisions, is_network, copay_pct, network_discount_pct)

    trace.add_event(TraceEvent(
        step=0,
        agent="PolicyEngine",
        status="SUCCESS",
        input_summary=f"member={member['name']}, amount=₹{submission.claimed_amount:,.0f}, network={is_network}",
        output_summary=f"{decision.value}: ₹{final_approved:,.2f} approved",
        checks=checks,
        confidence_delta=0.0,
        metadata={"breakdown": breakdown.model_dump()},
    ))

    return ClaimDecision(
        decision=decision,
        approved_amount=final_approved,
        reason=reason,
        line_item_decisions=line_decisions,
        financial_breakdown=breakdown,
        confidence_score=0.0,  # set by orchestrator from trace
    )


def _build_rejection_text(
    reasons: list[str],
    submission: ClaimSubmission,
    per_claim_limit: float,
    eligible_from_date: Optional[str],
) -> str:
    parts = []
    if RejectionReason.WAITING_PERIOD.value in reasons:
        parts.append(
            f"This claim falls within a waiting period. "
            f"{'You will be eligible from ' + eligible_from_date + '.' if eligible_from_date else ''}"
        )
    if RejectionReason.PRE_AUTH_MISSING.value in reasons:
        parts.append(
            "Pre-authorization was required for this procedure but was not obtained. "
            "Please contact Plum at least 48 hours before the procedure to get pre-authorization, then resubmit."
        )
    if RejectionReason.PER_CLAIM_EXCEEDED.value in reasons:
        parts.append(
            f"The claimed amount of ₹{submission.claimed_amount:,.0f} exceeds the per-claim limit of "
            f"₹{per_claim_limit:,.0f}. Only claims up to ₹{per_claim_limit:,.0f} per claim are covered."
        )
    if RejectionReason.EXCLUDED_CONDITION.value in reasons:
        parts.append(
            "The treatment or diagnosis is excluded under your policy. "
            "Excluded treatments include bariatric surgery, cosmetic procedures, obesity programs, LASIK, and orthodontic treatment."
        )
    if RejectionReason.ANNUAL_LIMIT_EXCEEDED.value in reasons:
        parts.append("Annual OPD limit has been exhausted for this policy year.")
    return " | ".join(parts) if parts else "Claim rejected."


def _build_approval_text(
    decision: Decision,
    breakdown: FinancialBreakdown,
    line_decisions: list[LineItemDecision],
    is_network: bool,
    copay_pct: float,
    network_discount_pct: float,
) -> str:
    parts = []
    if decision == Decision.PARTIAL:
        excluded = [d for d in line_decisions if not d.approved]
        parts.append(f"Partial approval: {len(excluded)} line item(s) excluded.")
        for d in excluded:
            parts.append(f"  - '{d.description}' (₹{d.amount:,.0f}): {d.reason}")
    if is_network and network_discount_pct > 0:
        parts.append(
            f"Network discount of {network_discount_pct * 100:.0f}% applied: "
            f"₹{breakdown.claimed_amount:,.2f} → ₹{breakdown.amount_after_discount:,.2f}."
        )
    if copay_pct > 0:
        parts.append(
            f"Co-pay of {copay_pct * 100:.0f}% deducted: ₹{breakdown.copay_amount:,.2f}."
        )
    parts.append(f"Final approved amount: ₹{breakdown.approved_amount:,.2f}.")
    return " ".join(parts)
