from __future__ import annotations
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import init_db, get_session, ClaimRecord
from models.claim import (
    ClaimSubmission, DocumentInput, DocumentType,
    DocumentQuality, ClaimsHistoryEntry, ClaimCategory,
)
from agents.orchestrator import process_claim
from pydantic import BaseModel
from typing import Optional


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Plum Claims Processor",
    description="AI-powered health insurance claims processing",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_test_cases() -> list[dict]:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_cases.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)['test_cases']


def _build_submission_from_tc(tc: dict) -> ClaimSubmission:
    inp = tc['input']
    docs = [
        DocumentInput(
            file_id=d['file_id'],
            file_name=d.get('file_name'),
            actual_type=DocumentType(d['actual_type']) if d.get('actual_type') else None,
            quality=DocumentQuality(d['quality']) if d.get('quality') else None,
            content=d.get('content'),
            patient_name_on_doc=d.get('patient_name_on_doc'),
        )
        for d in inp.get('documents', [])
    ]
    history = [
        ClaimsHistoryEntry(
            claim_id=h['claim_id'], date=h['date'],
            amount=h['amount'], provider=h.get('provider'),
        )
        for h in inp.get('claims_history', [])
    ]
    return ClaimSubmission(
        member_id=inp['member_id'],
        policy_id=inp['policy_id'],
        claim_category=ClaimCategory(inp['claim_category']),
        treatment_date=inp['treatment_date'],
        claimed_amount=float(inp['claimed_amount']),
        hospital_name=inp.get('hospital_name'),
        ytd_claims_amount=float(inp.get('ytd_claims_amount', 0)),
        claims_history=history,
        documents=docs,
        simulate_component_failure=inp.get('simulate_component_failure', False),
    )


def _evaluate_tc(tc: dict, result: dict) -> dict:
    expected = tc['expected']
    actual_decision = result['decision']['decision']
    passed = True
    notes = []

    if expected.get('decision') and actual_decision != expected['decision']:
        passed = False
        notes.append(f"Decision: got {actual_decision}, expected {expected['decision']}")
    else:
        notes.append(f"Decision: {actual_decision} ✓")

    expected_amount = expected.get('approved_amount')
    if expected_amount is not None:
        actual_amount = result['decision'].get('approved_amount', 0)
        if abs(actual_amount - expected_amount) > 0.01:
            passed = False
            notes.append(f"Amount: got ₹{actual_amount:.2f}, expected ₹{expected_amount:.2f}")
        else:
            notes.append(f"Amount: ₹{actual_amount:.2f} ✓")

    for r in expected.get('rejection_reasons', []):
        if r not in result['decision'].get('rejection_reasons', []):
            passed = False
            notes.append(f"Missing rejection reason: {r}")
        else:
            notes.append(f"Rejection reason: {r} ✓")

    return {'passed': passed, 'notes': notes}


def _upsert_record(session: AsyncSession, result: dict) -> ClaimRecord:
    return ClaimRecord(
        claim_id=result["claim_id"],
        member_id=result["member_id"],
        policy_id=result["policy_id"],
        claim_category=result["claim_category"],
        claimed_amount=result["claimed_amount"],
        decision=result["decision"]["decision"],
        approved_amount=result["decision"].get("approved_amount", 0.0),
        confidence_score=result["decision"].get("confidence_score", 0.0),
        reason=result["decision"].get("reason", ""),
        trace_json=json.dumps(result["trace"]),
        result_json=json.dumps(result),
    )


# ── Resubmit request body ──────────────────────────────────────────────────────

class ResubmitRequest(BaseModel):
    documents: list[DocumentInput]


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/claims/submit")
async def submit_claim(
    submission: ClaimSubmission,
    session: AsyncSession = Depends(get_session),
):
    result = await process_claim(submission)
    record = _upsert_record(session, result)
    session.add(record)
    await session.commit()
    return result


@app.post("/claims/{claim_id}/resubmit")
async def resubmit_claim(
    claim_id: str,
    body: ResubmitRequest,
    session: AsyncSession = Depends(get_session),
):
    """Re-run an existing claim with new documents, keeping the same claim ID."""
    row = await session.execute(select(ClaimRecord).where(ClaimRecord.claim_id == claim_id))
    record = row.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")

    original = json.loads(record.result_json)

    # Reconstruct the submission from the original data + new documents
    from datetime import date as _date
    treatment_date = original.get("treatment_date") or str(_date.today())
    submission = ClaimSubmission(
        member_id=original["member_id"],
        policy_id=original["policy_id"],
        claim_category=ClaimCategory(original["claim_category"]),
        treatment_date=treatment_date,
        claimed_amount=original["claimed_amount"],
        hospital_name=original.get("hospital_name"),
        ytd_claims_amount=original.get("ytd_claims_amount", 0.0),
        documents=body.documents,
    )

    result = await process_claim(submission, override_claim_id=claim_id)

    # Update existing record in place
    record.decision = result["decision"]["decision"]
    record.approved_amount = result["decision"].get("approved_amount", 0.0)
    record.confidence_score = result["decision"].get("confidence_score", 0.0)
    record.reason = result["decision"].get("reason", "")
    record.trace_json = json.dumps(result["trace"])
    record.result_json = json.dumps(result)
    await session.commit()

    return result


@app.get("/claims")
async def list_claims(
    session: AsyncSession = Depends(get_session),
    limit: int = 100,
    offset: int = 0,
    q: Optional[str] = None,
):
    query = select(ClaimRecord).order_by(ClaimRecord.created_at.desc())
    result = await session.execute(query.limit(limit).offset(offset))
    records = result.scalars().all()
    claims = [json.loads(r.result_json) for r in records]
    if q:
        q_lower = q.lower()
        claims = [
            c for c in claims
            if q_lower in c.get("claim_id", "").lower()
            or q_lower in c.get("member_id", "").lower()
            or q_lower in c.get("claim_category", "").lower()
            or q_lower in (c.get("hospital_name") or "").lower()
        ]
    return claims


@app.get("/claims/{claim_id}")
async def get_claim(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ClaimRecord).where(ClaimRecord.claim_id == claim_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Claim not found")
    return json.loads(record.result_json)


@app.get("/policy")
async def get_policy():
    from config import POLICY
    return POLICY


@app.get("/members")
async def list_members():
    from config import POLICY
    return POLICY.get("members", [])


@app.get("/test-cases")
async def list_test_cases():
    cases = _load_test_cases()
    return [
        {
            "case_id": tc["case_id"],
            "case_name": tc["case_name"],
            "description": tc.get("description", ""),
            "expected_decision": tc["expected"].get("decision"),
            "expected_amount": tc["expected"].get("approved_amount"),
        }
        for tc in cases
    ]


@app.post("/test-cases/{case_id}/run")
async def run_test_case(case_id: str, session: AsyncSession = Depends(get_session)):
    cases = _load_test_cases()
    tc = next((c for c in cases if c["case_id"] == case_id), None)
    if not tc:
        raise HTTPException(status_code=404, detail=f"Test case '{case_id}' not found")

    submission = _build_submission_from_tc(tc)
    result = await process_claim(submission)

    record = _upsert_record(session, result)
    session.add(record)
    await session.commit()

    evaluation = _evaluate_tc(tc, result)
    return {
        **result,
        "test_case": {
            "case_id": tc["case_id"],
            "case_name": tc["case_name"],
            "description": tc.get("description", ""),
            "expected_decision": tc["expected"].get("decision"),
            "expected_amount": tc["expected"].get("approved_amount"),
            "passed": evaluation["passed"],
            "eval_notes": evaluation["notes"],
        },
    }
