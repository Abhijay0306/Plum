import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listTestCases, runTestCase } from '../api/client'
import type { TestCaseMeta, TestCaseResult } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'

const CheckIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 1 }}>
    <polyline points="20 6 9 17 4 12"/>
  </svg>
)
const XIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 1 }}>
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
)

function EvalNote({ note }: { note: string }) {
  const isPass = note.includes('✓')
  const isFail = note.toLowerCase().includes('mismatch') || note.toLowerCase().includes('missing') || note.toLowerCase().includes('got')
  const color = isPass ? 'var(--status-approved-fg)' : isFail ? 'var(--status-rejected-fg)' : 'var(--text-tertiary)'
  const cleanNote = note.replace(' ✓', '')
  return (
    <div style={{
      fontSize: 12, color, padding: '2px 0',
      display: 'flex', gap: 6, alignItems: 'flex-start',
    }}>
      {isPass ? <CheckIcon /> : isFail ? <XIcon /> : <span style={{ flexShrink: 0, width: 12, textAlign: 'center' }}>·</span>}
      <span>{cleanNote}</span>
    </div>
  )
}

function TestCaseCard({ tc }: { tc: TestCaseMeta }) {
  const navigate = useNavigate()
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<TestCaseResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleRun = async () => {
    setRunning(true); setError(null); setResult(null)
    try { setResult(await runTestCase(tc.case_id)) }
    catch (e: unknown) { setError(e instanceof Error ? e.message : 'Failed') }
    finally { setRunning(false) }
  }

  const passed = result?.test_case.passed

  return (
    <div style={{
      background: 'var(--surface-card)',
      borderRadius: 'var(--radius-lg)',
      border: result
        ? `1.5px solid ${passed ? 'var(--status-approved-bd)' : 'var(--status-rejected-bd)'}`
        : '1px solid var(--border-default)',
      boxShadow: 'var(--shadow-sm)',
      overflow: 'hidden',
      transition: 'border-color 0.2s',
    }}>
      {/* Header */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border-default)', display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5, flexWrap: 'wrap' }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 500,
              color: '#141413', background: '#F3F0EE',
              padding: '2px 8px', borderRadius: 'var(--radius-pill)',
              border: '1px solid #D1CDC7',
            }}>{tc.case_id}</span>
            {tc.expected_decision && <DecisionBadge decision={tc.expected_decision} />}
            {tc.expected_amount !== null && (
              <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontVariantNumeric: 'tabular-nums' }}>
                ₹{tc.expected_amount.toLocaleString('en-IN')}
              </span>
            )}
          </div>
          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)', marginBottom: 2 }}>{tc.case_name}</div>
          {tc.description && (
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)', lineHeight: 1.5 }}>{tc.description}</div>
          )}
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          style={{
            padding: '7px 18px', borderRadius: 999,
            border: '1.5px solid #141413',
            background: running ? '#D1CDC7' : '#141413',
            color: running ? '#696969' : '#F3F0EE',
            fontWeight: 600, fontSize: 13, cursor: running ? 'not-allowed' : 'pointer',
            flexShrink: 0, fontFamily: 'var(--font-ui)',
            transition: 'background 0.15s',
            letterSpacing: '-0.01em',
          }}
        >
          {running ? 'Running…' : result ? 'Re-run' : 'Run'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{ padding: '10px 20px', background: 'var(--status-rejected-bg)', color: 'var(--status-rejected-fg)', fontSize: 13 }}>
          Error: {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div style={{ padding: '14px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
            <span style={{
              fontSize: 12, fontWeight: 700, padding: '3px 10px',
              borderRadius: 'var(--radius-pill)',
              background: passed ? 'var(--status-approved-bg)' : 'var(--status-rejected-bg)',
              color: passed ? 'var(--status-approved-fg)' : 'var(--status-rejected-fg)',
              border: `1px solid ${passed ? 'var(--status-approved-bd)' : 'var(--status-rejected-bd)'}`,
            }}>
              {passed ? 'PASS' : 'FAIL'}
            </span>
            <DecisionBadge decision={result.decision.decision} />
            <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
              ₹{result.decision.approved_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
              {(result.decision.confidence_score * 100).toFixed(1)}% conf
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 1, marginBottom: 10 }}>
            {result.test_case.eval_notes.map((n: string, i: number) => <EvalNote key={i} note={n} />)}
          </div>

          {result.decision.reason && (
            <div style={{
              fontSize: 12, color: 'var(--text-secondary)',
              background: 'var(--surface-sunken)', borderRadius: 'var(--radius-md)',
              padding: '8px 10px', marginBottom: 10, lineHeight: 1.5,
            }}>
              {result.decision.reason.slice(0, 180)}{result.decision.reason.length > 180 ? '…' : ''}
            </div>
          )}

          <button
            onClick={() => navigate(`/claims/${result.claim_id}`, { state: result })}
            style={{
              fontSize: 12, color: '#141413',
              background: 'none', border: '1.5px solid #141413',
              borderRadius: 999, padding: '5px 14px',
              cursor: 'pointer', fontWeight: 600, fontFamily: 'var(--font-ui)',
            }}
          >
            View full trace →
          </button>
        </div>
      )}
    </div>
  )
}

export default function TestCases() {
  const [cases, setCases] = useState<TestCaseMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [runningAll, setRunningAll] = useState(false)
  const [results, setResults] = useState<Map<string, TestCaseResult>>(new Map())

  useEffect(() => {
    listTestCases().then(c => { setCases(c); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const runAll = async () => {
    setRunningAll(true)
    const r = new Map<string, TestCaseResult>()
    for (const tc of cases) {
      try {
        const res = await runTestCase(tc.case_id)
        r.set(tc.case_id, res)
        setResults(new Map(r))
      } catch (_) { /* card handles individual errors */ }
    }
    setRunningAll(false)
  }

  if (loading) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>Loading test cases…</div>
  )

  const passCount = Array.from(results.values()).filter((r: TestCaseResult) => r.test_case.passed).length
  const totalRun = results.size

  return (
    <div style={{ maxWidth: 1000, margin: '0 auto', padding: '8px 32px 64px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em', marginBottom: 4 }}>
            Test Cases
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>
            {cases.length} predefined scenarios — run individually or all at once
          </p>
        </div>
        <button
          onClick={runAll}
          disabled={runningAll || cases.length === 0}
          style={{
            padding: '9px 24px', borderRadius: 999,
            border: '1.5px solid #141413',
            background: runningAll ? '#D1CDC7' : '#141413',
            color: runningAll ? '#696969' : '#F3F0EE',
            fontWeight: 600, fontSize: 13,
            cursor: runningAll ? 'not-allowed' : 'pointer',
            fontFamily: 'var(--font-ui)',
            letterSpacing: '-0.01em',
          }}
        >
          {runningAll ? 'Running all…' : 'Run All'}
        </button>
      </div>

      {totalRun > 0 && (
        <div style={{
          marginBottom: 20, padding: '10px 16px', borderRadius: 'var(--radius-md)',
          background: passCount === totalRun ? 'var(--status-approved-bg)' : 'var(--status-review-bg)',
          color: passCount === totalRun ? 'var(--status-approved-fg)' : 'var(--status-review-fg)',
          border: `1px solid ${passCount === totalRun ? 'var(--status-approved-bd)' : 'var(--status-review-bd)'}`,
          fontWeight: 600, fontSize: 14,
        }}>
          {passCount}/{totalRun} passed
          {passCount < totalRun && ` — ${totalRun - passCount} failing`}
        </div>
      )}

      <div style={{ display: 'grid', gap: 12 }}>
        {cases.map(tc => <TestCaseCard key={tc.case_id} tc={tc} />)}
      </div>
    </div>
  )
}
