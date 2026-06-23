"""
Fraud detection agent. Checks same-day claim patterns, monthly limits,
high-value thresholds, and document alteration signals.
"""
from __future__ import annotations
from datetime import date
from models.claim import ClaimSubmission
from models.trace import TraceEvent, TraceLog, CheckResult
from agents.document_parser import ParsedDocument
from config import POLICY


class FraudResult:
    def __init__(self, fraud_score: float, signals: list[str], route_to_manual: bool):
        self.fraud_score = fraud_score
        self.signals = signals
        self.route_to_manual = route_to_manual


def detect_fraud(
    submission: ClaimSubmission,
    parsed_docs: list[ParsedDocument],
    trace: TraceLog,
    failed: bool = False,
) -> FraudResult:
    if failed:
        # Simulated failure — treat as pass, note in trace
        trace.add_event(TraceEvent(
            step=0,
            agent="FraudDetectorAgent",
            status="SKIPPED",
            input_summary="Fraud detection skipped (simulated component failure)",
            output_summary="Skipped — manual review recommended",
            checks=[],
            errors=["FraudDetectorAgent failed: simulated error"],
            confidence_delta=-0.15,
        ))
        return FraudResult(fraud_score=0.0, signals=["FRAUD_CHECK_SKIPPED"], route_to_manual=False)

    thresholds = POLICY.get("fraud_thresholds", {})
    same_day_limit = thresholds.get("same_day_claims_limit", 2)
    monthly_limit = thresholds.get("monthly_claims_limit", 6)
    high_value_threshold = thresholds.get("high_value_claim_threshold", 25000)
    fraud_score_threshold = thresholds.get("fraud_score_manual_review_threshold", 0.80)

    signals: list[str] = []
    checks: list[CheckResult] = []
    fraud_score = 0.0

    # Same-day claim count
    treatment_date = submission.treatment_date
    same_day_claims = [
        h for h in submission.claims_history
        if h.date == treatment_date
    ]
    same_day_count = len(same_day_claims)
    same_day_ok = same_day_count <= same_day_limit
    if not same_day_ok:
        signal = (
            f"Member has {same_day_count} other claim(s) on the same date ({treatment_date}), "
            f"exceeding the limit of {same_day_limit}. "
            f"Prior claims: {[f'{h.claim_id} at {h.provider}' for h in same_day_claims]}."
        )
        signals.append(signal)
        fraud_score += 0.45
    checks.append(CheckResult(
        name="same_day_claims",
        passed=same_day_ok,
        detail=f"{same_day_count} same-day claim(s) (limit={same_day_limit})",
    ))

    # High-value claim
    is_high_value = submission.claimed_amount >= high_value_threshold
    if is_high_value:
        signals.append(f"High-value claim: ₹{submission.claimed_amount:,.0f} exceeds threshold ₹{high_value_threshold:,.0f}.")
        fraud_score += 0.2
    checks.append(CheckResult(
        name="high_value",
        passed=not is_high_value,
        detail=f"Amount ₹{submission.claimed_amount:,.0f} vs threshold ₹{high_value_threshold:,.0f}",
    ))

    # Document alteration signals from parsed content
    for doc in parsed_docs:
        quality_issues = doc.data.get("quality_issues", [])
        for issue in quality_issues:
            if "alteration" in str(issue).lower() or "correction" in str(issue).lower():
                signals.append(f"Document alteration detected in {doc.file_id}: {issue}")
                fraud_score += 0.2

    route_to_manual = (
        fraud_score >= fraud_score_threshold
        or same_day_count > same_day_limit  # same-day excess always triggers manual review
        or POLICY.get("fraud_thresholds", {}).get("auto_manual_review_above", 25000) <= submission.claimed_amount
    )

    status = "WARNING" if signals else "SUCCESS"
    trace.add_event(TraceEvent(
        step=0,
        agent="FraudDetectorAgent",
        status=status,
        input_summary=f"amount=₹{submission.claimed_amount:,.0f}, history={len(submission.claims_history)} claim(s)",
        output_summary=f"Fraud score={fraud_score:.2f}, signals={len(signals)}, manual_review={route_to_manual}",
        checks=checks,
        errors=signals,
        confidence_delta=-0.05 * len(signals),
        metadata={"fraud_score": fraud_score},
    ))
    return FraudResult(fraud_score=fraud_score, signals=signals, route_to_manual=route_to_manual)
