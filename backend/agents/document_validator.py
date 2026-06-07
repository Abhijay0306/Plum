"""
Validates that the correct document types have been uploaded for the claim category.
Pure logic — no LLM. Stops pipeline early with specific, actionable error messages.
"""
from __future__ import annotations
from models.claim import ClaimCategory, DocumentType, DocumentQuality
from models.trace import TraceEvent, TraceLog, CheckResult
from agents.document_classifier import ClassifiedDocument
from config import POLICY


_FRIENDLY_NAMES = {
    "PRESCRIPTION": "Doctor's Prescription (Rx)",
    "HOSPITAL_BILL": "Hospital / Clinic Bill or Invoice",
    "LAB_REPORT": "Diagnostic Lab Report",
    "PHARMACY_BILL": "Pharmacy Bill",
    "DISCHARGE_SUMMARY": "Discharge Summary",
    "DENTAL_REPORT": "Dental Examination Report",
    "DIAGNOSTIC_REPORT": "Diagnostic Imaging Report (MRI/CT/X-Ray)",
}


class DocumentValidationError(Exception):
    def __init__(self, errors: list[dict]):
        self.errors = errors
        super().__init__(str(errors))


class UnreadableDocumentError(Exception):
    def __init__(self, file_id: str, file_name: str | None):
        self.file_id = file_id
        self.file_name = file_name
        super().__init__(f"Unreadable: {file_id}")


def _friendly(doc_type: str) -> str:
    return _FRIENDLY_NAMES.get(doc_type, doc_type)


def validate_documents(
    category: ClaimCategory,
    docs: list[ClassifiedDocument],
    trace: TraceLog,
) -> None:
    """
    Raises DocumentValidationError if wrong/missing docs.
    Raises UnreadableDocumentError if a required doc is unreadable.
    """
    # Check for unreadable documents first
    for doc in docs:
        if doc.quality == DocumentQuality.UNREADABLE:
            trace.add_event(TraceEvent(
                step=0,
                agent="DocumentValidatorAgent",
                status="FAILED",
                input_summary=f"Category={category.value}, {len(docs)} doc(s)",
                output_summary=f"Unreadable document: {doc.file_id}",
                checks=[CheckResult(
                    name="document_readability",
                    passed=False,
                    detail=f"Document '{doc.file_name or doc.file_id}' cannot be read. Please re-upload a clearer image.",
                )],
                confidence_delta=-0.3,
            ))
            raise UnreadableDocumentError(doc.file_id, doc.file_name)

    req_config = POLICY.get("document_requirements", {}).get(category.value, {})
    required_types = set(req_config.get("required", []))
    present_types = {d.classified_type.value for d in docs}

    errors: list[dict] = []
    checks: list[CheckResult] = []

    for req in required_types:
        if req not in present_types:
            # Find what was uploaded instead
            uploaded_names = [_friendly(d.classified_type.value) for d in docs]
            errors.append({
                "missing_type": req,
                "missing_friendly": _friendly(req),
                "uploaded_types": uploaded_names,
                "message": (
                    f"You uploaded {' and '.join(uploaded_names) if uploaded_names else 'no documents'}, "
                    f"but a {_friendly(req)} is required for a {category.value} claim. "
                    f"Please upload a {_friendly(req)} and resubmit."
                ),
            })
            checks.append(CheckResult(
                name=f"required_{req}",
                passed=False,
                detail=f"Missing required document: {_friendly(req)}",
            ))
        else:
            checks.append(CheckResult(
                name=f"required_{req}",
                passed=True,
                detail=f"{_friendly(req)} present",
            ))

    status = "SUCCESS" if not errors else "FAILED"
    trace.add_event(TraceEvent(
        step=0,
        agent="DocumentValidatorAgent",
        status=status,
        input_summary=f"Category={category.value}, required={list(required_types)}, present={list(present_types)}",
        output_summary=f"{len(errors)} validation error(s)",
        checks=checks,
        errors=[e["message"] for e in errors],
        confidence_delta=-0.2 * len(errors),
    ))

    if errors:
        raise DocumentValidationError(errors)
