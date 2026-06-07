"""Unit tests for the deterministic policy engine."""
import pytest
from models.claim import ClaimSubmission, ClaimCategory, DocumentInput
from models.decision import Decision, RejectionReason
from models.trace import TraceLog
from engines.policy_engine import run_policy_checks
from agents.document_parser import ParsedDocument


def _make_trace() -> TraceLog:
    return TraceLog(claim_id="TEST")


def _parsed(data: dict) -> ParsedDocument:
    return ParsedDocument(file_id="F_TEST", doc_type="HOSPITAL_BILL", data=data, confidence=0.9, extraction_source="test")


def _submission(**kwargs) -> ClaimSubmission:
    defaults = dict(
        member_id="EMP001",
        policy_id="PLUM_GHI_2024",
        claim_category=ClaimCategory.CONSULTATION,
        treatment_date="2024-11-01",
        claimed_amount=1500.0,
        ytd_claims_amount=0.0,
        documents=[],
    )
    defaults.update(kwargs)
    return ClaimSubmission(**defaults)


class TestWaitingPeriod:
    def test_diabetes_within_waiting_period(self):
        sub = _submission(
            member_id="EMP005",
            treatment_date="2024-10-15",
            claimed_amount=3000.0,
        )
        docs = [_parsed({"diagnosis": "Type 2 Diabetes Mellitus", "medicines": ["Metformin 500mg"]})]
        result = run_policy_checks(sub, docs, _make_trace())
        assert result.decision == Decision.REJECTED
        assert RejectionReason.WAITING_PERIOD.value in result.rejection_reasons
        assert result.eligible_from_date == "2024-11-30"

    def test_normal_treatment_no_waiting_period(self):
        sub = _submission(treatment_date="2024-11-01")
        docs = [_parsed({"diagnosis": "Viral Fever"})]
        result = run_policy_checks(sub, docs, _make_trace())
        assert result.decision in (Decision.APPROVED, Decision.PARTIAL)


class TestPerClaimLimit:
    def test_claim_exceeds_per_claim_limit(self):
        sub = _submission(claimed_amount=7500.0)
        docs = [_parsed({"line_items": [{"description": "Consultation", "amount": 7500}]})]
        result = run_policy_checks(sub, docs, _make_trace())
        assert result.decision == Decision.REJECTED
        assert RejectionReason.PER_CLAIM_EXCEEDED.value in result.rejection_reasons

    def test_claim_within_per_claim_limit(self):
        sub = _submission(claimed_amount=1500.0)
        docs = [_parsed({"diagnosis": "Viral Fever", "line_items": [{"description": "Consultation", "amount": 1500}]})]
        result = run_policy_checks(sub, docs, _make_trace())
        assert result.decision in (Decision.APPROVED, Decision.PARTIAL)


class TestExclusions:
    def test_bariatric_excluded(self):
        sub = _submission(
            member_id="EMP009",
            claimed_amount=8000.0,
        )
        docs = [_parsed({
            "diagnosis": "Morbid Obesity — BMI 37",
            "treatment": "Bariatric Consultation",
            "line_items": [{"description": "Bariatric Consultation", "amount": 8000}],
        })]
        result = run_policy_checks(sub, docs, _make_trace())
        assert result.decision == Decision.REJECTED
        assert RejectionReason.EXCLUDED_CONDITION.value in result.rejection_reasons

    def test_dental_partial_cosmetic_excluded(self):
        sub = _submission(
            member_id="EMP002",
            claim_category=ClaimCategory.DENTAL,
            claimed_amount=12000.0,
        )
        docs = [_parsed({
            "line_items": [
                {"description": "Root Canal Treatment", "amount": 8000},
                {"description": "Teeth Whitening", "amount": 4000},
            ],
        })]
        result = run_policy_checks(sub, docs, _make_trace())
        assert result.decision == Decision.PARTIAL
        assert result.approved_amount == 8000.0
        approved = [d for d in result.line_item_decisions if d.approved]
        rejected = [d for d in result.line_item_decisions if not d.approved]
        assert len(approved) == 1
        assert len(rejected) == 1
        assert "Root Canal" in approved[0].description
        assert "Whitening" in rejected[0].description


class TestPreAuth:
    def test_mri_above_threshold_no_pre_auth(self):
        sub = _submission(
            member_id="EMP007",
            claim_category=ClaimCategory.DIAGNOSTIC,
            claimed_amount=15000.0,
        )
        docs = [_parsed({
            "tests_ordered": ["MRI Lumbar Spine"],
            "diagnosis": "Suspected Lumbar Disc Herniation",
            "line_items": [{"description": "MRI Lumbar Spine", "amount": 15000}],
        })]
        result = run_policy_checks(sub, docs, _make_trace())
        assert result.decision == Decision.REJECTED
        assert RejectionReason.PRE_AUTH_MISSING.value in result.rejection_reasons


class TestNetworkDiscount:
    def test_network_discount_applied_before_copay(self):
        sub = _submission(
            member_id="EMP010",
            claimed_amount=4500.0,
            hospital_name="Apollo Hospitals",
        )
        docs = [_parsed({
            "hospital_name": "Apollo Hospitals",
            "line_items": [
                {"description": "Consultation Fee", "amount": 1500},
                {"description": "Medicines", "amount": 3000},
            ],
        })]
        result = run_policy_checks(sub, docs, _make_trace())
        assert result.decision == Decision.APPROVED
        assert abs(result.approved_amount - 3240.0) < 0.01
        fb = result.financial_breakdown
        assert fb is not None
        assert abs(fb.network_discount_amount - 900.0) < 0.01
        assert abs(fb.copay_amount - 360.0) < 0.01


class TestCopay:
    def test_consultation_copay_10_percent(self):
        sub = _submission(claimed_amount=1500.0)
        docs = [_parsed({
            "diagnosis": "Viral Fever",
            "line_items": [{"description": "Consultation Fee", "amount": 1500}],
        })]
        result = run_policy_checks(sub, docs, _make_trace())
        assert result.decision == Decision.APPROVED
        assert abs(result.approved_amount - 1350.0) < 0.01


class TestMemberNotFound:
    def test_unknown_member_rejected(self):
        sub = _submission(member_id="EMP999")
        result = run_policy_checks(sub, [], _make_trace())
        assert result.decision == Decision.REJECTED
        assert RejectionReason.MEMBER_NOT_FOUND.value in result.rejection_reasons
