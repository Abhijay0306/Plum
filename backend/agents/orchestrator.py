"""
Orchestrator — coordinates the full multi-agent pipeline.
Each agent appends to a shared TraceLog.
Failures are caught, logged, confidence reduced, pipeline continues.
"""
from __future__ import annotations
import time
import uuid
from datetime import datetime
from typing import Optional

from models.claim import ClaimSubmission, ClaimCategory
from models.decision import ClaimDecision, Decision
from models.trace import TraceEvent, TraceLog
from agents.document_classifier import classify_documents
from agents.document_validator import (
    validate_documents, DocumentValidationError, UnreadableDocumentError
)
from agents.document_parser import parse_documents
from agents.cross_doc_validator import validate_patient_consistency, PatientMismatchError
from engines.policy_engine import run_policy_checks
from agents.fraud_detector import detect_fraud
from agents.decision_agent import finalize_decision
from config import POLICY


def _get_member_name(member_id: str) -> str:
    for m in POLICY.get("members", []):
        if m["member_id"] == member_id:
            return m["name"]
    return member_id


async def process_claim(submission: ClaimSubmission, override_claim_id: str | None = None) -> dict:
    claim_id = override_claim_id or f"CLM-{uuid.uuid4().hex[:8].upper()}"
    start_time = time.time()

    trace = TraceLog(claim_id=claim_id)
    member_name = _get_member_name(submission.member_id)

    # ── Step 1: Document Classification ─────────────────────────────────────
    try:
        classified_docs = await classify_documents(submission.documents, trace)
    except Exception as exc:
        trace.mark_degraded("DocumentClassifierAgent")
        trace.add_event(TraceEvent(
            step=0,
            agent="DocumentClassifierAgent",
            status="FAILED",
            input_summary="Document classification",
            output_summary=f"Failed: {exc}",
            errors=[str(exc)],
            confidence_delta=-0.2,
        ))
        classified_docs = []

    # ── Step 2: Document Validation (early exit) ─────────────────────────────
    try:
        validate_documents(submission.claim_category, classified_docs, trace)
    except UnreadableDocumentError as exc:
        return _early_exit_result(
            claim_id=claim_id,
            submission=submission,
            trace=trace,
            decision=Decision.REJECTED,
            reason=(
                f"Document '{exc.file_name or exc.file_id}' could not be read. "
                f"Please re-upload a clearer image of this document and resubmit."
            ),
            rejection_reasons=["UNREADABLE_DOCUMENT"],
            start_time=start_time,
            confidence=0.95,
        )
    except DocumentValidationError as exc:
        messages = " | ".join(e["message"] for e in exc.errors)
        return _early_exit_result(
            claim_id=claim_id,
            submission=submission,
            trace=trace,
            decision=Decision.REJECTED,
            reason=messages,
            rejection_reasons=["WRONG_DOCUMENT"],
            start_time=start_time,
            confidence=0.98,
        )
    except Exception as exc:
        trace.mark_degraded("DocumentValidatorAgent")
        trace.add_event(TraceEvent(
            step=0, agent="DocumentValidatorAgent", status="FAILED",
            input_summary="Document validation", output_summary=str(exc),
            errors=[str(exc)], confidence_delta=-0.15,
        ))

    # ── Step 3: Document Parsing ─────────────────────────────────────────────
    try:
        parsed_docs = await parse_documents(classified_docs, trace)
    except Exception as exc:
        trace.mark_degraded("DocumentParserAgent")
        trace.add_event(TraceEvent(
            step=0, agent="DocumentParserAgent", status="FAILED",
            input_summary="Document parsing", output_summary=str(exc),
            errors=[str(exc)], confidence_delta=-0.2,
        ))
        parsed_docs = []

    # ── Step 4: Cross-Document Patient Validation (early exit) ───────────────
    try:
        validate_patient_consistency(classified_docs, parsed_docs, member_name, trace)
    except PatientMismatchError as exc:
        messages = " | ".join(m["message"] for m in exc.mismatches)
        return _early_exit_result(
            claim_id=claim_id,
            submission=submission,
            trace=trace,
            decision=Decision.REJECTED,
            reason=messages,
            rejection_reasons=["PATIENT_MISMATCH"],
            start_time=start_time,
            confidence=0.95,
        )
    except Exception as exc:
        trace.mark_degraded("CrossDocValidatorAgent")
        trace.add_event(TraceEvent(
            step=0, agent="CrossDocValidatorAgent", status="FAILED",
            input_summary="Cross-doc validation", output_summary=str(exc),
            errors=[str(exc)], confidence_delta=-0.1,
        ))

    # ── Step 5: Policy Engine ────────────────────────────────────────────────
    policy_failed = False
    try:
        policy_decision = run_policy_checks(submission, parsed_docs, trace)
    except Exception as exc:
        policy_failed = True
        trace.mark_degraded("PolicyEngine")
        trace.add_event(TraceEvent(
            step=0, agent="PolicyEngine", status="FAILED",
            input_summary="Policy checks", output_summary=str(exc),
            errors=[str(exc)], confidence_delta=-0.3,
        ))
        policy_decision = ClaimDecision(
            decision=Decision.MANUAL_REVIEW,
            reason=f"Policy engine failed: {exc}. Manual review required.",
            confidence_score=0.3,
        )

    # ── Step 6: Fraud Detection ──────────────────────────────────────────────
    fraud_component_failed = submission.simulate_component_failure
    try:
        if fraud_component_failed:
            raise RuntimeError("Simulated component failure")
        fraud_result = detect_fraud(submission, parsed_docs, trace, failed=False)
    except Exception as exc:
        trace.mark_degraded("FraudDetectorAgent")
        fraud_result = detect_fraud(submission, parsed_docs, trace, failed=True)

    # ── Step 7: Decision Agent ───────────────────────────────────────────────
    submission_summary = {
        "member_id": submission.member_id,
        "claim_category": submission.claim_category.value,
        "claimed_amount": submission.claimed_amount,
        "treatment_date": submission.treatment_date,
        "same_day_claims": len(submission.claims_history),
    }
    try:
        final_decision = await finalize_decision(
            policy_decision, fraud_result, submission_summary, trace
        )
    except Exception as exc:
        trace.mark_degraded("DecisionAgent")
        trace.add_event(TraceEvent(
            step=0, agent="DecisionAgent", status="FAILED",
            input_summary="Decision finalization", output_summary=str(exc),
            errors=[str(exc)], confidence_delta=-0.1,
        ))
        final_decision = policy_decision
        final_decision.confidence_score = max(0.2, trace.final_confidence)
        final_decision.degraded = True
        final_decision.degraded_components = trace.degraded_components

    processing_time_ms = round((time.time() - start_time) * 1000, 1)

    return {
        "claim_id": claim_id,
        "member_id": submission.member_id,
        "policy_id": submission.policy_id,
        "claim_category": submission.claim_category.value,
        "claimed_amount": submission.claimed_amount,
        "treatment_date": submission.treatment_date,
        "hospital_name": submission.hospital_name,
        "ytd_claims_amount": submission.ytd_claims_amount,
        "decision": final_decision.model_dump(),
        "trace": [e.model_dump() for e in trace.events],
        "processing_time_ms": processing_time_ms,
        "created_at": datetime.utcnow().isoformat(),
    }


def _early_exit_result(
    claim_id: str,
    submission: ClaimSubmission,
    trace: TraceLog,
    decision: Decision,
    reason: str,
    rejection_reasons: list[str],
    start_time: float,
    confidence: float,
) -> dict:
    processing_time_ms = round((time.time() - start_time) * 1000, 1)
    return {
        "claim_id": claim_id,
        "member_id": submission.member_id,
        "policy_id": submission.policy_id,
        "claim_category": submission.claim_category.value,
        "claimed_amount": submission.claimed_amount,
        "treatment_date": submission.treatment_date,
        "hospital_name": submission.hospital_name,
        "ytd_claims_amount": submission.ytd_claims_amount,
        "decision": {
            "decision": decision.value,
            "approved_amount": 0.0,
            "reason": reason,
            "rejection_reasons": rejection_reasons,
            "line_item_decisions": [],
            "financial_breakdown": None,
            "confidence_score": confidence,
            "degraded": False,
            "degraded_components": [],
            "manual_review_signals": [],
            "eligible_from_date": None,
        },
        "trace": [e.model_dump() for e in trace.events],
        "processing_time_ms": processing_time_ms,
        "created_at": datetime.utcnow().isoformat(),
    }
