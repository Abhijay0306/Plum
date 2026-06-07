"""
Classifies each uploaded document's type using LLM vision.
If actual_type is provided (test mode), skips LLM and uses it directly.
"""
from __future__ import annotations
from models.claim import DocumentInput, DocumentType
from models.trace import TraceEvent, TraceLog
from services.llm_client import vision_chat, parse_json_response

_CLASSIFY_PROMPT = """You are a document classifier for Indian health insurance claims.

Examine the document and classify it as exactly ONE of:
- PRESCRIPTION — a doctor's Rx with diagnosis, medicines, doctor signature
- HOSPITAL_BILL — a hospital/clinic invoice or receipt with itemized charges
- LAB_REPORT — a diagnostic lab test report with test results and values
- PHARMACY_BILL — a pharmacy/chemist bill for medicines purchased
- DISCHARGE_SUMMARY — a hospital discharge summary document
- DENTAL_REPORT — a dental examination or procedure report
- DIAGNOSTIC_REPORT — imaging report (MRI, CT, X-Ray, USG findings)
- UNKNOWN — cannot determine

Respond ONLY with valid JSON:
{
  "classified_type": "<TYPE>",
  "confidence": <0.0-1.0>,
  "reasoning": "<one sentence>"
}"""


class ClassifiedDocument:
    def __init__(
        self,
        doc: DocumentInput,
        classified_type: DocumentType,
        confidence: float,
        reasoning: str,
    ):
        self.file_id = doc.file_id
        self.file_name = doc.file_name
        self.classified_type = classified_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.quality = doc.quality
        self.content = doc.content
        self.file_data = doc.file_data
        self.mime_type = doc.mime_type
        self.patient_name_on_doc = doc.patient_name_on_doc


async def classify_documents(
    documents: list[DocumentInput],
    trace: TraceLog,
) -> list[ClassifiedDocument]:
    results: list[ClassifiedDocument] = []

    for doc in documents:
        # Test mode: actual_type provided — skip LLM
        if doc.actual_type is not None:
            results.append(ClassifiedDocument(
                doc=doc,
                classified_type=doc.actual_type,
                confidence=1.0,
                reasoning="Type provided directly in submission (test mode).",
            ))
            continue

        # Real mode: use LLM vision
        try:
            raw = await vision_chat(
                prompt=_CLASSIFY_PROMPT,
                image_b64=doc.file_data,
                mime_type=doc.mime_type or "image/jpeg",
            )
            parsed = parse_json_response(raw)
            classified_type = DocumentType(parsed.get("classified_type", "UNKNOWN"))
            confidence = float(parsed.get("confidence", 0.5))
            reasoning = parsed.get("reasoning", "")
            results.append(ClassifiedDocument(
                doc=doc,
                classified_type=classified_type,
                confidence=confidence,
                reasoning=reasoning,
            ))
        except Exception as exc:
            results.append(ClassifiedDocument(
                doc=doc,
                classified_type=DocumentType.UNKNOWN,
                confidence=0.0,
                reasoning=f"Classification failed: {exc}",
            ))

    types_found = [r.classified_type.value for r in results]
    trace.add_event(TraceEvent(
        step=0,
        agent="DocumentClassifierAgent",
        status="SUCCESS",
        input_summary=f"{len(documents)} document(s) submitted",
        output_summary=f"Classified as: {types_found}",
        checks=[],
        confidence_delta=0.0,
    ))
    return results
