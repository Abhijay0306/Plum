import React, { useEffect, useState } from 'react'
import { useParams, useLocation, Link } from 'react-router-dom'
import { getClaim, resubmitClaim } from '../api/client'
import type { ClaimResult } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'
import TraceTimeline from '../components/TraceTimeline'
import DocUploadCard, { makeEmptyDoc } from '../components/DocUploadCard'
import type { DocEntry } from '../components/DocUploadCard'

// ─── Shared card style ────────────────────────────────────────────────────────
const card: React.CSSProperties = {
  background: 'var(--surface-card)',
  borderRadius: 'var(--radius-lg)',
  border: '1px solid var(--border-default)',
  boxShadow: 'var(--shadow-sm)',
  padding: 24,
  marginBottom: 16,
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)',
      letterSpacing: '0.05em', textTransform: 'uppercase',
      marginBottom: 16,
      paddingBottom: 10,
      borderBottom: '1px solid var(--border-default)',
    }}>{children}</div>
  )
}

function MetaRow({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: '1px solid var(--surface-sunken)' }}>
      <span style={{ fontSize: 12, color: 'var(--text-tertiary)', fontWeight: 500 }}>{label}</span>
      <span style={{
        fontSize: 13, fontWeight: 600, color: 'var(--text-primary)',
        fontFamily: mono ? 'var(--font-mono)' : 'var(--font-ui)',
      }}>{value}</span>
    </div>
  )
}

// ─── Reason cards ─────────────────────────────────────────────────────────────
function ReasonCards({ reason, decision }: { reason: string; decision: string }) {
  const isRejection = decision === 'REJECTED' || decision === 'MANUAL_REVIEW'
  const segments = isRejection && reason.includes(' | ')
    ? reason.split(' | ').filter(Boolean)
    : [reason]

  const colors = {
    REJECTED:      { bg: 'var(--status-rejected-bg)', bd: 'var(--status-rejected-bd)', text: 'var(--status-rejected-fg)' },
    MANUAL_REVIEW: { bg: 'var(--status-docs-bg)',     bd: 'var(--status-docs-bd)',     text: 'var(--status-docs-fg)' },
    PARTIAL:       { bg: 'var(--status-review-bg)',   bd: 'var(--status-review-bd)',   text: 'var(--status-review-fg)' },
    APPROVED:      { bg: 'var(--status-approved-bg)', bd: 'var(--status-approved-bd)', text: 'var(--status-approved-fg)' },
  }
  const c = colors[decision as keyof typeof colors] ?? colors.APPROVED

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {segments.map((seg, i) => {
        const actionMatch = seg.match(/^(.*?)\.\s*(Please .+|Contact .+)$/s)
        const problem = actionMatch ? actionMatch[1].trim() : seg.trim()
        const action = actionMatch ? actionMatch[2].trim() : null

        return (
          <div key={i} style={{ background: c.bg, border: `1px solid ${c.bd}`, borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
            <div style={{ fontSize: 14, color: c.text, lineHeight: 1.55, fontWeight: 500 }}>{problem}</div>
            {action && (
              <div style={{
                marginTop: 8, padding: '8px 12px',
                background: 'var(--surface-card)', borderRadius: 6, border: `1px solid ${c.bd}`,
                fontSize: 13, color: 'var(--text-primary)', fontWeight: 600,
                display: 'flex', alignItems: 'flex-start', gap: 8,
              }}>
                <span style={{ flexShrink: 0, color: c.text }}>→</span>
                <span>{action}</span>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─── Resubmit section ─────────────────────────────────────────────────────────
const RESUBMITTABLE = new Set(['WRONG_DOCUMENT', 'UNREADABLE_DOCUMENT', 'PATIENT_MISMATCH'])

function ResubmitSection({ claim, onResubmit }: { claim: ClaimResult; onResubmit: (result: ClaimResult) => void }) {
  const [open, setOpen] = useState(false)
  const [docs, setDocs] = useState<DocEntry[]>([makeEmptyDoc()])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mergeDoc = (uid: string, updates: Partial<DocEntry>) =>
    setDocs(d => d.map(doc => doc.uid === uid ? { ...doc, ...updates } : doc))
  const addDoc = () => setDocs(d => [...d, makeEmptyDoc()])
  const removeDoc = (uid: string) => setDocs(d => d.filter(x => x.uid !== uid))

  const handleResubmit = async () => {
    const withFiles = docs.filter(d => d.file_data)
    if (withFiles.length === 0) return setError('Please upload at least one document.')
    setSubmitting(true); setError(null)
    try {
      const result = await resubmitClaim(
        claim.claim_id,
        withFiles.map((d, i) => ({
          file_id: `F${String(i + 1).padStart(3, '0')}`,
          file_name: d.file_name, file_data: d.file_data, mime_type: d.mime_type,
          patient_name_on_doc: d.patient_name_on_doc || undefined,
        })),
      )
      setOpen(false)
      setDocs([makeEmptyDoc()])
      onResubmit(result)
    } catch (e: unknown) {
      const axiosDetail = (e as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
      const msg = typeof axiosDetail === 'string'
        ? axiosDetail
        : (e instanceof Error ? e.message : 'Resubmission failed.')
      setError(msg)
    } finally { setSubmitting(false) }
  }

  return (
    <div style={{ border: '1.5px solid var(--plum-300)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', marginBottom: 16 }}>
      <button onClick={() => setOpen(o => !o)} style={{
        width: '100%', padding: '14px 20px',
        background: open ? 'var(--plum-700)' : 'var(--plum-50)',
        border: 'none', cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        transition: 'background 0.15s',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, textAlign: 'left' }}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" style={{ color: open ? '#fff' : 'var(--plum-500)', flexShrink: 0 }}><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>
          <div>
            <div style={{ fontWeight: 700, fontSize: 14, color: open ? '#fff' : 'var(--plum-700)' }}>
              Resubmit with Correct Documents
            </div>
            <div style={{ fontSize: 12, color: open ? 'var(--plum-200)' : 'var(--text-tertiary)', marginTop: 2 }}>
              All other claim details are pre-filled — just upload the correct files
            </div>
          </div>
        </div>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: open ? '#fff' : 'var(--plum-500)', flexShrink: 0 }}>{open ? <polyline points="18 15 12 9 6 15"/> : <polyline points="6 9 12 15 18 9"/>}</svg>
      </button>

      {open && (
        <div style={{ padding: 20, background: 'var(--surface-card)' }}>
          <div style={{
            background: 'var(--plum-50)', borderRadius: 'var(--radius-md)',
            padding: '10px 14px', marginBottom: 16,
            fontSize: 13, color: 'var(--text-secondary)',
            border: '1px solid var(--plum-200)',
          }}>
            <strong style={{ color: 'var(--text-primary)' }}>Pre-filled:</strong>{' '}
            {claim.member_id} · {claim.claim_category} · ₹{claim.claimed_amount.toLocaleString('en-IN')}
            {claim.treatment_date ? ` · ${claim.treatment_date}` : ''}
            {claim.hospital_name ? ` · ${claim.hospital_name}` : ''}
          </div>

          {docs.map((doc, i) => (
            <DocUploadCard key={doc.uid} doc={doc} index={i}
              onRemove={() => removeDoc(doc.uid)}
              onMerge={updates => mergeDoc(doc.uid, updates)} />
          ))}

          <button type="button" onClick={addDoc} style={{
            width: '100%', padding: 9, borderRadius: 'var(--radius-md)',
            border: '1px dashed var(--border-strong)',
            background: 'var(--surface-sunken)', color: 'var(--text-secondary)',
            cursor: 'pointer', fontSize: 13, fontWeight: 600, marginBottom: 14,
          }}>+ Add Another Document</button>

          {error && (
            <div style={{ background: 'var(--status-rejected-bg)', border: '1px solid var(--status-rejected-bd)', borderRadius: 'var(--radius-md)', padding: 10, marginBottom: 12, color: 'var(--status-rejected-fg)', fontSize: 13 }}>
              {error}
            </div>
          )}

          <button onClick={handleResubmit} disabled={submitting} style={{
            width: '100%', padding: 12, borderRadius: 'var(--radius-md)', border: 'none',
            background: submitting ? 'var(--plum-300)' : 'var(--plum-500)',
            color: '#fff', fontWeight: 700, fontSize: 14, cursor: submitting ? 'not-allowed' : 'pointer',
            fontFamily: 'var(--font-ui)',
          }}>
            {submitting ? 'Processing… (AI reading your documents)' : 'Resubmit Claim →'}
          </button>
        </div>
      )}
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────
export default function ClaimDetail() {
  const { claimId } = useParams()
  const { state } = useLocation()
  const [claim, setClaim] = useState<ClaimResult | null>(state as ClaimResult | null)
  const [loading, setLoading] = useState(!state)

  useEffect(() => {
    if (!state && claimId) {
      getClaim(claimId).then(c => { setClaim(c); setLoading(false) }).catch(() => setLoading(false))
    }
  }, [claimId, state])

  if (loading) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>Loading…</div>
  if (!claim) return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)' }}>Claim not found.</div>

  const d = claim.decision
  const fb = d.financial_breakdown

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24, gap: 16, flexWrap: 'wrap' }}>
        <div>
          <Link to="/claims" style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'inline-flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
            ← All Claims
          </Link>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <h1 style={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 500, color: 'var(--plum-500)', letterSpacing: '0.02em' }}>
              {claim.claim_id}
            </h1>
            <DecisionBadge decision={d.decision} />
            {d.degraded && (
              <span style={{ fontSize: 11, background: 'var(--status-review-bg)', color: 'var(--status-review-fg)', border: '1px solid var(--status-review-bd)', padding: '3px 10px', borderRadius: 'var(--radius-pill)', fontWeight: 600, letterSpacing: '0.04em' }}>
                ⚠ DEGRADED
              </span>
            )}
          </div>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
          {new Date(claim.created_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
          <span style={{ marginLeft: 8, color: 'var(--text-disabled)' }}>· {claim.processing_time_ms}ms</span>
        </div>
      </div>

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 16, alignItems: 'start' }}>

        {/* Left column */}
        <div>
          {/* Decision reason */}
          <div style={card}>
            <SectionHeading>
              {d.decision === 'REJECTED' ? 'Why was this rejected?' :
               d.decision === 'MANUAL_REVIEW' ? 'Why does this need review?' :
               d.decision === 'PARTIAL' ? 'Why was this partially approved?' :
               'Decision Summary'}
            </SectionHeading>
            <ReasonCards reason={d.reason} decision={d.decision} />
            {d.manual_review_signals.length > 0 && (
              <div style={{ marginTop: 12, background: 'var(--status-review-bg)', borderRadius: 'var(--radius-md)', padding: 12, borderLeft: '3px solid var(--status-review-fg)' }}>
                <div style={{ fontWeight: 700, fontSize: 12, color: 'var(--status-review-fg)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.04em' }}>⚠ Fraud Signals</div>
                {d.manual_review_signals.map((s, i) => (
                  <div key={i} style={{ fontSize: 12, color: 'var(--status-review-fg)', padding: '2px 0' }}>• {s}</div>
                ))}
              </div>
            )}
          </div>

          {/* Resubmit */}
          {d.rejection_reasons.some(r => RESUBMITTABLE.has(r)) && (
            <ResubmitSection claim={claim} onResubmit={updated => setClaim(updated)} />
          )}

          {/* Line items */}
          {d.line_item_decisions.length > 0 && (
            <div style={card}>
              <SectionHeading>Line Item Decisions</SectionHeading>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: 'var(--surface-sunken)' }}>
                    {['Description', 'Claimed', 'Status', 'Approved', 'Reason'].map(h => (
                      <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {d.line_item_decisions.map((item, i) => (
                    <tr key={i} style={{ borderTop: '1px solid var(--border-default)', background: item.approved ? 'transparent' : 'var(--status-rejected-bg)' }}>
                      <td style={{ padding: '9px 12px', fontWeight: 500 }}>{item.description}</td>
                      <td style={{ padding: '9px 12px', fontVariantNumeric: 'tabular-nums' }}>₹{item.amount.toLocaleString('en-IN')}</td>
                      <td style={{ padding: '9px 12px' }}>
                        <span style={{ fontSize: 12, fontWeight: 600, color: item.approved ? 'var(--status-approved-fg)' : 'var(--status-rejected-fg)' }}>
                          {item.approved ? '✓ Approved' : '✗ Rejected'}
                        </span>
                      </td>
                      <td style={{ padding: '9px 12px', fontVariantNumeric: 'tabular-nums', fontWeight: 600 }}>₹{item.approved_amount.toLocaleString('en-IN')}</td>
                      <td style={{ padding: '9px 12px', color: 'var(--text-secondary)', fontSize: 12 }}>{item.reason ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Degraded warning */}
          {d.degraded_components.length > 0 && (
            <div style={{ ...card, border: '1px solid var(--status-review-bd)', background: 'var(--status-review-bg)' }}>
              <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--status-review-fg)', marginBottom: 6 }}>⚠ Processing Degraded</div>
              <p style={{ fontSize: 13, color: 'var(--status-review-fg)' }}>
                Failed components: <strong>{d.degraded_components.join(', ')}</strong>. Results may be incomplete — manual review recommended.
              </p>
            </div>
          )}

          {/* Trace */}
          <div style={card}>
            <SectionHeading>Processing Trace</SectionHeading>
            <TraceTimeline events={claim.trace} />
          </div>
        </div>

        {/* Right column — sticky summary */}
        <div style={{ position: 'sticky', top: 72 }}>
          <div style={card}>
            <SectionHeading>Claim Summary</SectionHeading>
            <MetaRow label="Member" value={claim.member_id} />
            <MetaRow label="Category" value={claim.claim_category} />
            <MetaRow label="Policy" value={claim.policy_id} mono />
            {claim.treatment_date && <MetaRow label="Treatment Date" value={claim.treatment_date} />}
            {claim.hospital_name && <MetaRow label="Hospital" value={claim.hospital_name} />}
            <MetaRow label="Confidence" value={`${(d.confidence_score * 100).toFixed(1)}%`} />
            {d.eligible_from_date && <MetaRow label="Eligible From" value={d.eligible_from_date} />}
          </div>

          {/* Financial breakdown */}
          {fb && (
            <div style={card}>
              <SectionHeading>Financial Breakdown</SectionHeading>

              {claim.claimed_amount !== fb.claimed_amount && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--surface-sunken)', fontSize: 13 }}>
                  <span style={{ color: 'var(--text-tertiary)' }}>Submitted</span>
                  <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>₹{claim.claimed_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--surface-sunken)', fontSize: 13 }}>
                <span style={{ color: 'var(--text-tertiary)' }}>Eligible Base</span>
                <span style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>₹{fb.claimed_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
              {fb.network_discount_amount > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--surface-sunken)', fontSize: 13 }}>
                  <span style={{ color: 'var(--text-tertiary)' }}>Network Discount</span>
                  <span style={{ color: 'var(--status-approved-fg)', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>− ₹{fb.network_discount_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
              )}
              {fb.copay_amount > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '7px 0', borderBottom: '1px solid var(--surface-sunken)', fontSize: 13 }}>
                  <span style={{ color: 'var(--text-tertiary)' }}>Co-pay</span>
                  <span style={{ color: 'var(--status-rejected-fg)', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>− ₹{fb.copay_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>
              )}

              <div style={{ borderTop: '2px solid var(--plum-200)', marginTop: 8, paddingTop: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Approved</span>
                <span style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, color: 'var(--status-approved-fg)', fontVariantNumeric: 'tabular-nums' }}>
                  ₹{fb.approved_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
