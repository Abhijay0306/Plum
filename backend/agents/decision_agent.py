"""
Decision agent — synthesizes policy result, fraud result, and trace
into the final ClaimDecision. Uses LLM for ambiguous/manual-review cases.
"""
from __future__ import annotations
from models.decision import ClaimDecision, Decision
from models.trace import TraceEvent, TraceLog, CheckResult
from agents.fraud_detector import FraudResult
from services.llm_client import chat, parse_json_response
from config import REASONING_MODEL
import json


_MANUAL_REVIEW_PROMPT = """You are a senior claims analyst at an Indian health insurance company.

A claim has been flagged for manual review. Based on the details below, provide a brief assessment.

Claim Details:
{claim_details}

Fraud Signals:
{fraud_signals}

Policy Check Result:
{policy_result}

Respond ONLY with valid JSON:
{{
  "assessment": "<2-3 sentence assessment>",
  "key_concerns": ["<concern 1>", "<concern 2>"],
  "recommendation": "APPROVE_WITH_CAUTION | REJECT | ESCALATE"
}}"""


async def finalize_decision(
    policy_decision: ClaimDecision,
    fraud_result: FraudResult,
    submission_summary: dict,
    trace: TraceLog,
) -> ClaimDecision:
    checks: list[CheckResult] = []

    # If fraud signals route to manual review, override decision
    if fraud_result.route_to_manual and policy_decision.decision in (Decision.APPROVED, Decision.PARTIAL):
        # Use LLM to assess
        try:
            prompt = _MANUAL_REVIEW_PROMPT.format(
                claim_details=json.dumps(submission_summary, indent=2),
                fraud_signals=json.dumps(fraud_result.signals, indent=2),
                policy_result=policy_decision.reason,
            )
            raw = await chat(
                messages=[{"role": "user", "content": prompt}],
                model=REASONING_MODEL,
                max_tokens=512,
            )
            parsed = parse_json_response(raw)
            assessment = parsed.get("assessment", "")
            concerns = parsed.get("key_concerns", fraud_result.signals)
            checks.append(CheckResult(
                name="llm_assessment",
                passed=True,
                detail=f"LLM recommendation: {parsed.get('recommendation', 'ESCALATE')}",
            ))
        except Exception as exc:
            assessment = "Manual review required due to fraud signals."
            concerns = fraud_result.signals
            checks.append(CheckResult(
                name="llm_assessment",
                passed=False,
                detail=f"LLM assessment failed: {exc}. Using rule-based fallback.",
            ))

        final = ClaimDecision(
            decision=Decision.MANUAL_REVIEW,
            approved_amount=0.0,
            reason=(
                f"Claim flagged for manual review. {assessment} "
                f"Fraud score: {fraud_result.fraud_score:.2f}."
            ),
            manual_review_signals=fraud_result.signals,
            rejection_reasons=policy_decision.rejection_reasons,
            line_item_decisions=policy_decision.line_item_decisions,
            financial_breakdown=policy_decision.financial_breakdown,
            confidence_score=max(0.3, trace.final_confidence - 0.1),
            degraded=len(trace.degraded_components) > 0,
            degraded_components=trace.degraded_components,
        )
    else:
        final = ClaimDecision(
            decision=policy_decision.decision,
            approved_amount=policy_decision.approved_amount,
            reason=policy_decision.reason,
            rejection_reasons=policy_decision.rejection_reasons,
            line_item_decisions=policy_decision.line_item_decisions,
            financial_breakdown=policy_decision.financial_breakdown,
            eligible_from_date=policy_decision.eligible_from_date,
            manual_review_signals=fraud_result.signals,
            confidence_score=trace.final_confidence,
            degraded=len(trace.degraded_components) > 0,
            degraded_components=trace.degraded_components,
        )
        checks.append(CheckResult(
            name="decision_finalized",
            passed=True,
            detail=f"{final.decision.value}: ₹{final.approved_amount:,.2f}",
        ))

    degraded_note = ""
    if final.degraded:
        degraded_note = f" NOTE: {', '.join(trace.degraded_components)} failed during processing — manual review recommended."
        final.reason += degraded_note

    trace.add_event(TraceEvent(
        step=0,
        agent="DecisionAgent",
        status="SUCCESS",
        input_summary=f"policy={policy_decision.decision.value}, fraud_score={fraud_result.fraud_score:.2f}",
        output_summary=f"Final: {final.decision.value} (confidence={final.confidence_score:.2f})",
        checks=checks,
        confidence_delta=0.0,
    ))
    return final
