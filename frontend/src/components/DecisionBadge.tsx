const STATUS_MAP: Record<string, { fg: string; bg: string; bd: string; label: string }> = {
  APPROVED:      { fg: 'var(--status-approved-fg)',  bg: 'var(--status-approved-bg)',  bd: 'var(--status-approved-bd)',  label: 'Approved' },
  PARTIAL:       { fg: 'var(--status-review-fg)',    bg: 'var(--status-review-bg)',    bd: 'var(--status-review-bd)',    label: 'Partial' },
  REJECTED:      { fg: 'var(--status-rejected-fg)',  bg: 'var(--status-rejected-bg)',  bd: 'var(--status-rejected-bd)',  label: 'Rejected' },
  MANUAL_REVIEW: { fg: 'var(--status-docs-fg)',      bg: 'var(--status-docs-bg)',      bd: 'var(--status-docs-bd)',      label: 'Manual Review' },
}

export default function DecisionBadge({ decision }: { decision: string }) {
  const s = STATUS_MAP[decision] ?? { fg: 'var(--text-secondary)', bg: 'var(--surface-sunken)', bd: 'var(--border-default)', label: decision }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 10px',
      borderRadius: 'var(--radius-pill)',
      border: `1px solid ${s.bd}`,
      background: s.bg,
      color: s.fg,
      fontSize: 11,
      fontWeight: 600,
      letterSpacing: '0.04em',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
      fontFamily: 'var(--font-ui)',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: s.fg, flexShrink: 0 }} />
      {s.label}
    </span>
  )
}
