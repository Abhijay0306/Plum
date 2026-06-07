"""
Eval runner for all 12 test cases from test_cases.json.
Runs each case through the claims pipeline and produces a report.

Usage:
    cd backend
    python ../tests/eval_runner.py
    python ../tests/eval_runner.py --case TC004   # single case
    python ../tests/eval_runner.py --output eval_report.json
"""
from __future__ import annotations
import asyncio
import json
import sys
import os
import argparse
from datetime import datetime
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from models.claim import ClaimSubmission, ClaimCategory, DocumentInput, ClaimsHistoryEntry, DocumentType, DocumentQuality
from agents.orchestrator import process_claim


def _load_test_cases() -> list[dict]:
    path = os.path.join(os.path.dirname(__file__), '..', 'test_cases.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)['test_cases']


def _build_submission(tc: dict) -> ClaimSubmission:
    inp = tc['input']
    docs = []
    for d in inp.get('documents', []):
        doc = DocumentInput(
            file_id=d['file_id'],
            file_name=d.get('file_name'),
            actual_type=DocumentType(d['actual_type']) if d.get('actual_type') else None,
            quality=DocumentQuality(d['quality']) if d.get('quality') else None,
            content=d.get('content'),
            patient_name_on_doc=d.get('patient_name_on_doc'),
        )
        docs.append(doc)

    history = []
    for h in inp.get('claims_history', []):
        history.append(ClaimsHistoryEntry(
            claim_id=h['claim_id'],
            date=h['date'],
            amount=h['amount'],
            provider=h.get('provider'),
        ))

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


def _evaluate(tc: dict, result: dict) -> dict[str, Any]:
    expected = tc['expected']
    actual_decision = result['decision']['decision']
    expected_decision = expected.get('decision')

    passed = True
    notes = []

    # Decision match
    if expected_decision is not None:
        if actual_decision != expected_decision:
            passed = False
            notes.append(f"Decision mismatch: got '{actual_decision}', expected '{expected_decision}'")
        else:
            notes.append(f"Decision correct: {actual_decision}")

    # Approved amount
    expected_amount = expected.get('approved_amount')
    if expected_amount is not None:
        actual_amount = result['decision'].get('approved_amount', 0)
        if abs(actual_amount - expected_amount) > 0.01:
            passed = False
            notes.append(f"Amount mismatch: got ₹{actual_amount:.2f}, expected ₹{expected_amount:.2f}")
        else:
            notes.append(f"Amount correct: ₹{actual_amount:.2f}")

    # Confidence
    conf_spec = expected.get('confidence_score', '')
    if 'above' in str(conf_spec):
        threshold = float(str(conf_spec).replace('above', '').strip())
        actual_conf = result['decision'].get('confidence_score', 0)
        if actual_conf < threshold:
            passed = False
            notes.append(f"Confidence too low: got {actual_conf:.2f}, expected above {threshold}")
        else:
            notes.append(f"Confidence OK: {actual_conf:.2f}")

    # Rejection reasons
    expected_reasons = expected.get('rejection_reasons', [])
    if expected_reasons:
        actual_reasons = result['decision'].get('rejection_reasons', [])
        for r in expected_reasons:
            if r not in actual_reasons:
                passed = False
                notes.append(f"Missing rejection reason: {r}")
            else:
                notes.append(f"Rejection reason present: {r}")

    # system_must checks (qualitative — checked against reason/trace text)
    system_must = expected.get('system_must', [])
    for must in system_must:
        reason_text = result['decision'].get('reason', '').lower()
        trace_text = json.dumps(result.get('trace', [])).lower()
        combined = reason_text + trace_text
        # Simple keyword heuristics per requirement
        if 'stop' in must.lower() or 'not proceed' in must.lower():
            # Check that no final APPROVED/PARTIAL was returned
            if actual_decision in ('APPROVED', 'PARTIAL'):
                passed = False
                notes.append(f"system_must FAIL: '{must}' — system still approved")
            else:
                notes.append(f"system_must OK: stopped before approval")
        elif 'specific' in must.lower() or 'name' in must.lower() or 'document type' in must.lower():
            notes.append(f"system_must (qualitative): '{must}' — see reason field")
        elif 'eligible' in must.lower() or 'date' in must.lower():
            if result['decision'].get('eligible_from_date'):
                notes.append(f"system_must OK: eligible_from_date present")
            else:
                notes.append(f"system_must NOTE: '{must}' — eligible_from_date not set")
        elif 'manual review' in must.lower() or 'flag' in must.lower():
            if actual_decision == 'MANUAL_REVIEW' or result['decision'].get('manual_review_signals'):
                notes.append(f"system_must OK: manual review flagged")
            else:
                notes.append(f"system_must NOTE: '{must}' — not explicitly flagged")
        else:
            notes.append(f"system_must (check manually): '{must}'")

    return {'passed': passed, 'notes': notes}


async def run_case(tc: dict) -> dict:
    submission = _build_submission(tc)
    try:
        result = await process_claim(submission)
    except Exception as exc:
        result = {
            'claim_id': 'ERROR',
            'decision': {'decision': 'ERROR', 'reason': str(exc), 'approved_amount': 0, 'confidence_score': 0,
                         'rejection_reasons': [], 'manual_review_signals': [], 'degraded_components': [], 'degraded': True},
            'trace': [],
        }
    evaluation = _evaluate(tc, result)
    return {
        'case_id': tc['case_id'],
        'case_name': tc['case_name'],
        'passed': evaluation['passed'],
        'eval_notes': evaluation['notes'],
        'result': result,
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', help='Run a single case by ID (e.g. TC004)')
    parser.add_argument('--output', help='Save JSON report to file')
    args = parser.parse_args()

    test_cases = _load_test_cases()
    if args.case:
        test_cases = [tc for tc in test_cases if tc['case_id'] == args.case]
        if not test_cases:
            print(f"Case {args.case} not found.")
            sys.exit(1)

    print(f"\n{'='*70}")
    print(f"  PLUM CLAIMS EVAL RUNNER — {len(test_cases)} case(s)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    report = []
    passed_count = 0

    for tc in test_cases:
        print(f"Running {tc['case_id']}: {tc['case_name']}...", end=' ', flush=True)
        case_result = await run_case(tc)
        report.append(case_result)
        status = '✓ PASS' if case_result['passed'] else '✗ FAIL'
        decision = case_result['result']['decision']['decision']
        amount = case_result['result']['decision'].get('approved_amount', 0)
        conf = case_result['result']['decision'].get('confidence_score', 0)
        print(f"{status} | {decision} | ₹{amount:.0f} | conf={conf:.2f}")
        for note in case_result['eval_notes']:
            print(f"    → {note}")
        if case_result['passed']:
            passed_count += 1
        print()

    print(f"{'='*70}")
    print(f"  RESULTS: {passed_count}/{len(test_cases)} passed")
    print(f"{'='*70}\n")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Report saved to {args.output}")

    return report


if __name__ == '__main__':
    asyncio.run(main())
