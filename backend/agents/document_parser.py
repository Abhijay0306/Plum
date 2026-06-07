"""
Extracts structured information from each document.
In test mode (content field present), uses the provided dict directly.
In real mode, uses LLM vision to extract fields.
"""
from __future__ import annotations
from typing import Any, Optional
from models.trace import TraceEvent, TraceLog, CheckResult
from agents.document_classifier import ClassifiedDocument
from services.llm_client import vision_chat, parse_json_response

_PARSE_PROMPT = """You are an expert at extracting structured information from Indian medical documents.

Extract ALL available fields from this document. Be thorough — include partial or uncertain information and flag it.

Return ONLY valid JSON with this structure (omit fields you cannot find):
{
  "patient_name": "",
  "patient_age": null,
  "patient_gender": "",
  "date": "",
  "doctor_name": "",
  "doctor_registration": "",
  "hospital_name": "",
  "diagnosis": "",
  "medicines": [],
  "tests_ordered": [],
  "line_items": [{"description": "", "amount": 0}],
  "total_amount": null,
  "bill_number": "",
  "gstin": "",
  "test_results": [],
  "remarks": "",
  "confidence": 0.9,
  "unextracted_fields": [],
  "quality_issues": []
}"""


class ParsedDocument:
    def __init__(
        self,
        file_id: str,
        doc_type: str,
        data: dict[str, Any],
        confidence: float,
        extraction_source: str,
    ):
        self.file_id = file_id
        self.doc_type = doc_type
        self.data = data
        self.confidence = confidence
        self.extraction_source = extraction_source

    @property
    def patient_name(self) -> Optional[str]:
        return self.data.get("patient_name") or self.data.get("content", {}).get("patient_name") if isinstance(self.data.get("content"), dict) else self.data.get("patient_name")

    @property
    def total_amount(self) -> Optional[float]:
        v = self.data.get("total_amount") or self.data.get("total")
        return float(v) if v is not None else None

    @property
    def line_items(self) -> list[dict]:
        return self.data.get("line_items", [])

    @property
    def diagnosis(self) -> Optional[str]:
        return self.data.get("diagnosis")

    @property
    def hospital_name(self) -> Optional[str]:
        return self.data.get("hospital_name")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


async def parse_documents(
    docs: list[ClassifiedDocument],
    trace: TraceLog,
) -> list[ParsedDocument]:
    results: list[ParsedDocument] = []
    checks: list[CheckResult] = []
    confidence_delta = 0.0

    for doc in docs:
        if doc.content is not None:
            # Test mode: content already provided
            parsed = ParsedDocument(
                file_id=doc.file_id,
                doc_type=doc.classified_type.value,
                data=doc.content,
                confidence=0.95,
                extraction_source="test_content",
            )
            checks.append(CheckResult(
                name=f"parse_{doc.file_id}",
                passed=True,
                detail=f"{doc.classified_type.value}: extracted from test content",
            ))
        elif doc.file_data:
            try:
                raw = await vision_chat(
                    prompt=_PARSE_PROMPT,
                    image_b64=doc.file_data,
                    mime_type=doc.mime_type or "image/jpeg",
                )
                data = parse_json_response(raw)
                conf = float(data.pop("confidence", 0.8))
                parsed = ParsedDocument(
                    file_id=doc.file_id,
                    doc_type=doc.classified_type.value,
                    data=data,
                    confidence=conf,
                    extraction_source="llm_vision",
                )
                if conf < 0.5:
                    confidence_delta -= 0.1
                checks.append(CheckResult(
                    name=f"parse_{doc.file_id}",
                    passed=True,
                    detail=f"{doc.classified_type.value}: LLM extracted (confidence={conf:.2f})",
                ))
            except Exception as exc:
                parsed = ParsedDocument(
                    file_id=doc.file_id,
                    doc_type=doc.classified_type.value,
                    data={},
                    confidence=0.3,
                    extraction_source="failed",
                )
                confidence_delta -= 0.15
                checks.append(CheckResult(
                    name=f"parse_{doc.file_id}",
                    passed=False,
                    detail=f"Parse failed: {exc}",
                ))
        else:
            parsed = ParsedDocument(
                file_id=doc.file_id,
                doc_type=doc.classified_type.value,
                data={},
                confidence=0.5,
                extraction_source="no_file",
            )
            checks.append(CheckResult(
                name=f"parse_{doc.file_id}",
                passed=False,
                detail="No file data provided",
            ))

        results.append(parsed)

    trace.add_event(TraceEvent(
        step=0,
        agent="DocumentParserAgent",
        status="SUCCESS",
        input_summary=f"Parsing {len(docs)} document(s)",
        output_summary=f"Parsed {len(results)} document(s)",
        checks=checks,
        confidence_delta=confidence_delta,
    ))
    return results
