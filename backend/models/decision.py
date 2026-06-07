from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class Decision(str, Enum):
    APPROVED = "APPROVED"
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class RejectionReason(str, Enum):
    WRONG_DOCUMENT = "WRONG_DOCUMENT"
    UNREADABLE_DOCUMENT = "UNREADABLE_DOCUMENT"
    PATIENT_MISMATCH = "PATIENT_MISMATCH"
    WAITING_PERIOD = "WAITING_PERIOD"
    PRE_AUTH_MISSING = "PRE_AUTH_MISSING"
    PER_CLAIM_EXCEEDED = "PER_CLAIM_EXCEEDED"
    SUB_LIMIT_EXCEEDED = "SUB_LIMIT_EXCEEDED"
    ANNUAL_LIMIT_EXCEEDED = "ANNUAL_LIMIT_EXCEEDED"
    EXCLUDED_CONDITION = "EXCLUDED_CONDITION"
    FRAUD_DETECTED = "FRAUD_DETECTED"
    MEMBER_NOT_FOUND = "MEMBER_NOT_FOUND"
    POLICY_INACTIVE = "POLICY_INACTIVE"


class LineItemDecision(BaseModel):
    description: str
    amount: float
    approved: bool
    approved_amount: float
    reason: Optional[str] = None


class FinancialBreakdown(BaseModel):
    claimed_amount: float
    network_discount_amount: float = 0.0
    amount_after_discount: float = 0.0
    copay_amount: float = 0.0
    approved_amount: float = 0.0
    sub_limit_cap: Optional[float] = None
    per_claim_cap: Optional[float] = None


class ClaimDecision(BaseModel):
    decision: Decision
    approved_amount: float = 0.0
    reason: str
    rejection_reasons: list[str] = Field(default_factory=list)
    line_item_decisions: list[LineItemDecision] = Field(default_factory=list)
    financial_breakdown: Optional[FinancialBreakdown] = None
    confidence_score: float
    degraded: bool = False
    degraded_components: list[str] = Field(default_factory=list)
    manual_review_signals: list[str] = Field(default_factory=list)
    eligible_from_date: Optional[str] = None


class ClaimResult(BaseModel):
    claim_id: str
    member_id: str
    policy_id: str
    claim_category: str
    claimed_amount: float
    decision: ClaimDecision
    trace: list[dict]
    processing_time_ms: float
    created_at: str
