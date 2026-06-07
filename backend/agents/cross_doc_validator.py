"""
Checks that all documents belong to the same patient.
Surfaces mismatches with specific names found on each document.
"""
from __future__ import annotations
from models.trace import TraceEvent, TraceLog, CheckResult
from agents.document_classifier import ClassifiedDocument
from agents.document_parser import ParsedDocument


class PatientMismatchError(Exception):
    def __init__(self, mismatches: list[dict]):
        self.mismatches = mismatches
        super().__init__(str(mismatches))


def _normalize(name: str | None) -> str:
    if not name:
        return ""
    return " ".join(name.strip().lower().split())


def _names_match(a: str, b: str) -> bool:
    if not a or not b:
        return True  # Can't compare if name is missing
    na, nb = _normalize(a), _normalize(b)
    # Allow partial match (first name match) for common Indian name variations
    if na == nb:
        return True
    parts_a = set(na.split())
    parts_b = set(nb.split())
    # At least one common token of length > 2
    common = parts_a & parts_b
    return any(len(t) > 2 for t in common)


def validate_patient_consistency(
    docs: list[ClassifiedDocument],
    parsed: list[ParsedDocument],
    member_name: str,
    trace: TraceLog,
) -> None:
    """Raises PatientMismatchError if documents have inconsistent patient names."""
    names_by_doc: list[tuple[str, str | None]] = []

    for classified, p in zip(docs, parsed):
        # Prefer patient_name_on_doc (explicitly set in test cases) over parsed
        name = classified.patient_name_on_doc or p.data.get("patient_name")
        names_by_doc.append((classified.file_id, name))

    mismatches: list[dict] = []
    checks: list[CheckResult] = []

    for file_id, name in names_by_doc:
        if name and not _names_match(name, member_name):
            mismatches.append({
                "file_id": file_id,
                "found_name": name,
                "expected_name": member_name,
                "message": (
                    f"Document '{file_id}' belongs to '{name}', "
                    f"but the claim is filed by '{member_name}'. "
                    f"Please ensure all documents are for the same patient."
                ),
            })
            checks.append(CheckResult(
                name=f"patient_name_{file_id}",
                passed=False,
                detail=f"Name on doc: '{name}' ≠ member: '{member_name}'",
            ))
        else:
            checks.append(CheckResult(
                name=f"patient_name_{file_id}",
                passed=True,
                detail=f"Name matches: '{name or 'not found'}'",
            ))

    # Also check cross-doc consistency (docs must agree with each other)
    known_names = [(fid, n) for fid, n in names_by_doc if n]
    if len(known_names) >= 2:
        ref_id, ref_name = known_names[0]
        for fid, name in known_names[1:]:
            if not _names_match(ref_name, name):
                mismatches.append({
                    "file_id": fid,
                    "found_name": name,
                    "expected_name": ref_name,
                    "message": (
                        f"Document '{ref_id}' is for '{ref_name}' but "
                        f"document '{fid}' is for '{name}'. "
                        f"All documents must belong to the same patient."
                    ),
                })
                checks.append(CheckResult(
                    name=f"cross_doc_{fid}_vs_{ref_id}",
                    passed=False,
                    detail=f"'{name}' ≠ '{ref_name}'",
                ))

    status = "FAILED" if mismatches else "SUCCESS"
    trace.add_event(TraceEvent(
        step=0,
        agent="CrossDocValidatorAgent",
        status=status,
        input_summary=f"Checking {len(names_by_doc)} document(s) against member '{member_name}'",
        output_summary=f"{len(mismatches)} mismatch(es) found",
        checks=checks,
        errors=[m["message"] for m in mismatches],
        confidence_delta=-0.25 * len(mismatches),
    ))

    if mismatches:
        raise PatientMismatchError(mismatches)
