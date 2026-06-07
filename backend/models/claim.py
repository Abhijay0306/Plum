from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ClaimCategory(str, Enum):
    CONSULTATION = "CONSULTATION"
    DIAGNOSTIC = "DIAGNOSTIC"
    PHARMACY = "PHARMACY"
    DENTAL = "DENTAL"
    VISION = "VISION"
    ALTERNATIVE_MEDICINE = "ALTERNATIVE_MEDICINE"


class DocumentType(str, Enum):
    PRESCRIPTION = "PRESCRIPTION"
    HOSPITAL_BILL = "HOSPITAL_BILL"
    LAB_REPORT = "LAB_REPORT"
    PHARMACY_BILL = "PHARMACY_BILL"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    DENTAL_REPORT = "DENTAL_REPORT"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    UNKNOWN = "UNKNOWN"


class DocumentQuality(str, Enum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    UNREADABLE = "UNREADABLE"


class ClaimsHistoryEntry(BaseModel):
    claim_id: str
    date: str
    amount: float
    provider: Optional[str] = None


class DocumentInput(BaseModel):
    file_id: str
    file_name: Optional[str] = None
    # actual_type is provided in test cases to bypass classification
    actual_type: Optional[DocumentType] = None
    quality: Optional[DocumentQuality] = None
    # structured content provided by test cases (replaces real file parsing)
    content: Optional[dict[str, Any]] = None
    # real file upload: base64-encoded bytes + mime type
    file_data: Optional[str] = None
    mime_type: Optional[str] = None
    # meta fields from test cases
    patient_name_on_doc: Optional[str] = None


class ClaimSubmission(BaseModel):
    member_id: str
    policy_id: str
    claim_category: ClaimCategory
    treatment_date: str
    claimed_amount: float
    hospital_name: Optional[str] = None
    ytd_claims_amount: float = 0.0
    claims_history: list[ClaimsHistoryEntry] = Field(default_factory=list)
    documents: list[DocumentInput] = Field(default_factory=list)
    simulate_component_failure: bool = False
