"""Unit tests for document validator and cross-doc validator."""
import pytest
from models.claim import ClaimCategory, DocumentType, DocumentQuality
from models.trace import TraceLog
from agents.document_classifier import ClassifiedDocument
from agents.document_validator import validate_documents, DocumentValidationError, UnreadableDocumentError
from agents.cross_doc_validator import validate_patient_consistency, PatientMismatchError
from agents.document_parser import ParsedDocument


def _trace() -> TraceLog:
    return TraceLog(claim_id="TEST")


def _classified(file_id: str, doc_type: DocumentType, quality: DocumentQuality = DocumentQuality.GOOD, patient_name: str | None = None):
    from models.claim import DocumentInput
    doc = DocumentInput(file_id=file_id, actual_type=doc_type, quality=quality, patient_name_on_doc=patient_name)
    return ClassifiedDocument(doc=doc, classified_type=doc_type, confidence=1.0, reasoning="test")


def _parsed(file_id: str, patient_name: str | None = None):
    return ParsedDocument(file_id=file_id, doc_type="HOSPITAL_BILL", data={"patient_name": patient_name}, confidence=0.9, extraction_source="test")


class TestDocumentValidator:
    def test_wrong_doc_type_raises(self):
        docs = [
            _classified("F001", DocumentType.PRESCRIPTION),
            _classified("F002", DocumentType.PRESCRIPTION),  # should be HOSPITAL_BILL
        ]
        with pytest.raises(DocumentValidationError) as exc:
            validate_documents(ClaimCategory.CONSULTATION, docs, _trace())
        errors = exc.value.errors
        assert len(errors) > 0
        assert "HOSPITAL_BILL" in errors[0]["missing_friendly"] or "Hospital" in errors[0]["message"]

    def test_correct_docs_pass(self):
        docs = [
            _classified("F001", DocumentType.PRESCRIPTION),
            _classified("F002", DocumentType.HOSPITAL_BILL),
        ]
        # Should not raise
        validate_documents(ClaimCategory.CONSULTATION, docs, _trace())

    def test_unreadable_doc_raises(self):
        docs = [
            _classified("F001", DocumentType.PRESCRIPTION, DocumentQuality.GOOD),
            _classified("F002", DocumentType.PHARMACY_BILL, DocumentQuality.UNREADABLE),
        ]
        with pytest.raises(UnreadableDocumentError):
            validate_documents(ClaimCategory.PHARMACY, docs, _trace())

    def test_error_message_is_specific(self):
        docs = [_classified("F001", DocumentType.PRESCRIPTION)]
        with pytest.raises(DocumentValidationError) as exc:
            validate_documents(ClaimCategory.CONSULTATION, docs, _trace())
        msg = exc.value.errors[0]["message"]
        assert "PRESCRIPTION" in msg.upper() or "prescription" in msg.lower()
        assert "HOSPITAL_BILL" in msg.upper() or "hospital" in msg.lower()


class TestCrossDocValidator:
    def test_mismatched_patient_names_raises(self):
        classified = [
            _classified("F001", DocumentType.PRESCRIPTION, patient_name="Rajesh Kumar"),
            _classified("F002", DocumentType.HOSPITAL_BILL, patient_name="Arjun Mehta"),
        ]
        parsed = [_parsed("F001", "Rajesh Kumar"), _parsed("F002", "Arjun Mehta")]
        with pytest.raises(PatientMismatchError) as exc:
            validate_patient_consistency(classified, parsed, "Rajesh Kumar", _trace())
        assert len(exc.value.mismatches) > 0
        mismatch_msg = exc.value.mismatches[0]["message"]
        assert "Arjun Mehta" in mismatch_msg

    def test_matching_names_pass(self):
        classified = [
            _classified("F001", DocumentType.PRESCRIPTION, patient_name="Rajesh Kumar"),
            _classified("F002", DocumentType.HOSPITAL_BILL, patient_name="Rajesh Kumar"),
        ]
        parsed = [_parsed("F001", "Rajesh Kumar"), _parsed("F002", "Rajesh Kumar")]
        # Should not raise
        validate_patient_consistency(classified, parsed, "Rajesh Kumar", _trace())

    def test_missing_name_does_not_fail(self):
        classified = [
            _classified("F001", DocumentType.PRESCRIPTION),
            _classified("F002", DocumentType.HOSPITAL_BILL),
        ]
        parsed = [_parsed("F001", None), _parsed("F002", None)]
        # Should not raise when names are missing
        validate_patient_consistency(classified, parsed, "Rajesh Kumar", _trace())
