import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { listClaims } from '../api/client'
import type { ClaimResult } from '../api/client'
import DecisionBadge from '../components/DecisionBadge'

export default function ClaimsList() {
  const [claims, setClaims] = useState<ClaimResult[]>([])
  const [loading, setLoading] = useState(true)
  const [hovered, setHovered] = useState<string | null>(null)
  const [searchParams] = useSearchParams()
  const q = searchParams.get('q')?.toLowerCase().trim() ?? ''

  useEffect(() => {
    listClaims().then(c => { setClaims(c); setLoading(false) }).catch(() => setLoading(false))
  }, [])

  const filtered = q
    ? claims.filter(c =>
        c.claim_id.toLowerCase().includes(q) ||
        c.member_id.toLowerCase().includes(q) ||
        c.claim_category.toLowerCase().includes(q) ||
        (c.hospital_name ?? '').toLowerCase().includes(q)
      )
    : claims

  if (loading) return (
    <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-tertiary)', fontFamily: 'var(--font-ui)' }}>
      Loading claims…
    </div>
  )

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '8px 32px 64px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
            {q ? `Search: "${q}"` : 'All Claims'}
            <span style={{ marginLeft: 10, fontSize: 13, fontWeight: 500, color: 'var(--text-tertiary)' }}>
              ({filtered.length}{q && claims.length !== filtered.length ? ` of ${claims.length}` : ''})
            </span>
          </h1>
          {q && (
            <Link to="/claims" style={{ fontSize: 12, color: 'var(--plum-500)', marginTop: 4, display: 'inline-block' }}>
              ← Clear search
            </Link>
          )}
        </div>
        <Link to="/" style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '8px 20px', borderRadius: 999,
          background: '#141413', color: '#F3F0EE',
          fontSize: 13, fontWeight: 600,
          letterSpacing: '-0.01em',
          border: '1.5px solid #141413',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New Claim
        </Link>
      </div>

      {filtered.length === 0 ? (
        <div style={{
          background: 'var(--surface-card)', borderRadius: 'var(--radius-xl)',
          padding: '64px 48px', textAlign: 'center',
          border: '1px solid var(--border-default)',
          boxShadow: 'var(--shadow-sm)',
        }}>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 20, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
            {q ? 'No matching claims' : 'Clear skies ahead'}
          </div>
          <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 24 }}>
            {q ? `No claims found matching "${q}".` : 'No claims submitted yet. Start by filing your first claim.'}
          </div>
          <Link to={q ? '/claims' : '/'} style={{
            display: 'inline-flex', padding: '9px 20px', borderRadius: 999,
            background: '#141413', color: '#F3F0EE', fontSize: 13, fontWeight: 600,
            border: '1.5px solid #141413',
          }}>
            {q ? 'Clear search' : 'Submit First Claim →'}
          </Link>
        </div>
      ) : (
        <div style={{
          background: 'var(--surface-card)',
          borderRadius: 'var(--radius-xl)',
          border: '1px solid var(--border-default)',
          boxShadow: 'var(--shadow-sm)',
          overflow: 'hidden',
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--surface-sunken)', borderBottom: '1px solid var(--border-default)' }}>
                {['Claim ID', 'Member', 'Category', 'Claimed', 'Approved', 'Decision', 'Confidence', 'Date'].map(h => (
                  <th key={h} style={{
                    padding: '10px 16px',
                    textAlign: 'left',
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--text-tertiary)',
                    letterSpacing: '0.05em',
                    textTransform: 'uppercase',
                    whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(c => (
                <tr
                  key={c.claim_id}
                  onMouseEnter={() => setHovered(c.claim_id)}
                  onMouseLeave={() => setHovered(null)}
                  style={{
                    borderBottom: '1px solid var(--border-default)',
                    background: hovered === c.claim_id ? '#F3F0EE' : 'transparent',
                    transition: 'background 0.1s',
                  }}
                >
                  <td style={{ padding: '14px 16px' }}>
                    <Link to={`/claims/${c.claim_id}`} style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 13,
                      color: '#141413',
            textDecoration: 'underline',
                      fontWeight: 500,
                      letterSpacing: '0.02em',
                    }}>
                      {c.claim_id}
                    </Link>
                  </td>
                  <td style={{ padding: '14px 16px', fontSize: 13, color: 'var(--text-primary)', fontWeight: 500 }}>
                    {c.member_id}
                  </td>
                  <td style={{ padding: '14px 16px', fontSize: 13, color: 'var(--text-secondary)' }}>
                    {c.claim_category}
                  </td>
                  <td style={{ padding: '14px 16px', fontSize: 13, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
                    ₹{c.claimed_amount.toLocaleString('en-IN')}
                  </td>
                  <td style={{ padding: '14px 16px', fontSize: 13, fontWeight: 600, color: 'var(--status-approved-fg)', fontVariantNumeric: 'tabular-nums' }}>
                    ₹{c.decision.approved_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <DecisionBadge decision={c.decision.decision} />
                  </td>
                  <td style={{ padding: '14px 16px', fontSize: 13, color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
                    {(c.decision.confidence_score * 100).toFixed(1)}%
                  </td>
                  <td style={{ padding: '14px 16px', fontSize: 12, color: 'var(--text-tertiary)', fontVariantNumeric: 'tabular-nums' }}>
                    {new Date(c.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
