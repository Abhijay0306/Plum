import { useState } from 'react'
import type { TraceEvent } from '../api/client'

const STATUS_COLORS: Record<string, string> = {
  SUCCESS: 'var(--status-approved-fg)',
  FAILED:  'var(--status-rejected-fg)',
  WARNING: 'var(--status-review-fg)',
  SKIPPED: 'var(--text-tertiary)',
}

function CheckRow({ check }: { check: { name: string; passed: boolean; detail: string } }) {
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '3px 0' }}>
      <span style={{ color: check.passed ? 'var(--status-approved-fg)' : 'var(--status-rejected-fg)', fontSize: 12, flexShrink: 0, marginTop: 1 }}>
        {check.passed ? '✓' : '✗'}
      </span>
      <div>
        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{check.name}: </span>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{check.detail}</span>
      </div>
    </div>
  )
}

function TraceStep({ event, index, isLast }: { event: TraceEvent; index: number; isLast: boolean }) {
  const [open, setOpen] = useState(false)
  const color = STATUS_COLORS[event.status] ?? 'var(--text-secondary)'

  return (
    <div style={{ display: 'flex', gap: 14 }}>
      {/* Timeline thread */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 22, flexShrink: 0 }}>
        <div style={{
          width: 22, height: 22, borderRadius: '50%',
          background: color, color: '#fff',
          fontSize: 10, fontWeight: 700,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>{index + 1}</div>
        {!isLast && <div style={{ width: 2, flex: 1, background: 'var(--border-default)', margin: '4px 0', minHeight: 16 }} />}
      </div>

      {/* Content */}
      <div style={{ flex: 1, paddingBottom: isLast ? 0 : 16 }}>
        <div
          onClick={() => setOpen(o => !o)}
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>{event.agent}</span>
            <span style={{
              fontSize: 10, padding: '2px 7px',
              borderRadius: 'var(--radius-pill)',
              background: color + '18', color, fontWeight: 700,
              letterSpacing: '0.04em', textTransform: 'uppercase',
            }}>{event.status}</span>
          </div>
          <span style={{ fontSize: 11, color: 'var(--text-tertiary)', flexShrink: 0 }}>{open ? '▲' : '▼'}</span>
        </div>

        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3, lineHeight: 1.5 }}>
          {event.output_summary}
          {event.confidence_delta !== 0 && (
            <span style={{
              marginLeft: 6, fontWeight: 700,
              color: event.confidence_delta < 0 ? 'var(--status-rejected-fg)' : 'var(--status-approved-fg)',
            }}>
              {event.confidence_delta > 0 ? '+' : ''}{(event.confidence_delta * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {open && (
          <div style={{ marginTop: 10, background: 'var(--surface-sunken)', borderRadius: 'var(--radius-md)', padding: 12 }}>
            <div style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 10, lineHeight: 1.5 }}>
              <strong style={{ color: 'var(--text-secondary)' }}>Input:</strong> {event.input_summary}
            </div>

            {event.checks.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
                  Checks
                </div>
                {event.checks.map((c, i) => <CheckRow key={i} check={c} />)}
              </div>
            )}

            {event.errors.length > 0 && (
              <div style={{ background: 'var(--status-rejected-bg)', borderRadius: 'var(--radius-sm)', padding: '8px 10px', border: '1px solid var(--status-rejected-bd)' }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--status-rejected-fg)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Issues</div>
                {event.errors.map((e, i) => (
                  <div key={i} style={{ color: 'var(--status-rejected-fg)', fontSize: 12, marginBottom: 2 }}>• {e}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default function TraceTimeline({ events }: { events: TraceEvent[] }) {
  if (!events.length) return <p style={{ color: 'var(--text-tertiary)', fontSize: 13 }}>No trace events.</p>
  return (
    <div>
      {events.map((e, i) => <TraceStep key={i} event={e} index={i} isLast={i === events.length - 1} />)}
    </div>
  )
}
