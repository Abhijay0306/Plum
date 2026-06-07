"""Unit tests for fraud detection."""
import pytest
from models.claim import ClaimSubmission, ClaimCategory, ClaimsHistoryEntry
from models.trace import TraceLog
from agents.fraud_detector import detect_fraud
from agents.document_parser import ParsedDocument


def _trace() -> TraceLog:
    return TraceLog(claim_id="TEST")


def _parsed():
    return ParsedDocument(file_id="F1", doc_type="HOSPITAL_BILL", data={}, confidence=0.9, extraction_source="test")


def _submission(**kwargs) -> ClaimSubmission:
    defaults = dict(
        member_id="EMP008",
        policy_id="PLUM_GHI_2024",
        claim_category=ClaimCategory.CONSULTATION,
        treatment_date="2024-10-30",
        claimed_amount=4800.0,
        documents=[],
    )
    defaults.update(kwargs)
    return ClaimSubmission(**defaults)


class TestFraudDetector:
    def test_same_day_excess_triggers_manual_review(self):
        sub = _submission(
            claims_history=[
                ClaimsHistoryEntry(claim_id="CLM_001", date="2024-10-30", amount=1200, provider="Clinic A"),
                ClaimsHistoryEntry(claim_id="CLM_002", date="2024-10-30", amount=1800, provider="Clinic B"),
                ClaimsHistoryEntry(claim_id="CLM_003", date="2024-10-30", amount=2100, provider="Wellness"),
            ]
        )
        result = detect_fraud(sub, [_parsed()], _trace())
        assert result.route_to_manual is True
        assert result.fraud_score > 0
        assert len(result.signals) > 0
        # Signal must mention same-day pattern
        combined = " ".join(result.signals)
        assert "same" in combined.lower() or "day" in combined.lower()

    def test_no_fraud_signals_for_clean_claim(self):
        sub = _submission(claimed_amount=1500.0)
        result = detect_fraud(sub, [_parsed()], _trace())
        assert result.fraud_score < 0.5

    def test_simulated_failure_returns_manual_review(self):
        sub = _submission()
        result = detect_fraud(sub, [_parsed()], _trace(), failed=True)
        assert result.route_to_manual is True
        assert "FRAUD_CHECK_SKIPPED" in result.signals
