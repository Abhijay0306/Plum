import { useRef, useState } from 'react'

export interface DocEntry {
  uid: string
  file_name: string
  file_data: string
  mime_type: string
  patient_name_on_doc: string
  preview: string | null
  size_kb: number
}

export function makeEmptyDoc(uid?: string): DocEntry {
  return {
    uid: uid ?? `doc-${Date.now()}`,
    file_name: '', file_data: '', mime_type: '',
    patient_name_on_doc: '', preview: null, size_kb: 0,
  }
}

export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve((reader.result as string).split(',')[1])
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', borderRadius: 'var(--radius-md)',
  border: '1px solid var(--border-default)', fontSize: 13, outline: 'none',
  boxSizing: 'border-box', fontFamily: 'var(--font-ui)', background: 'var(--surface-card)',
  color: 'var(--text-primary)',
}
const label: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6,
}

export default function DocUploadCard({
  doc,
  index,
  onRemove,
  onMerge,
}: {
  doc: DocEntry
  index: number
  onRemove: () => void
  onMerge: (updates: Partial<DocEntry>) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handleFile = async (file: File) => {
    if (!file.type.startsWith('image/') && file.type !== 'application/pdf') return
    const b64 = await fileToBase64(file)
    const preview = file.type.startsWith('image/') ? await fileToDataUrl(file) : null
    onMerge({
      file_name: file.name,
      file_data: b64,
      mime_type: file.type,
      preview,
      size_kb: Math.round(file.size / 1024),
    })
  }

  const isEmpty = !doc.file_data

  return (
    <div style={{
      border: '1px solid var(--border-default)', borderRadius: 'var(--radius-lg)',
      padding: 16, marginBottom: 12,
      background: 'var(--surface-sunken)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <span style={{ fontWeight: 600, fontSize: 13, color: '#6b7280' }}>Document {index + 1}</span>
        <button type="button" onClick={onRemove}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-tertiary)', padding: '4px', borderRadius: 4, display: 'flex', alignItems: 'center' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      {isEmpty ? (
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f) }}
          onClick={() => inputRef.current?.click()}
          style={{
            border: `2px dashed ${dragging ? 'var(--plum-500)' : 'var(--border-strong)'}`,
            borderRadius: 'var(--radius-md)', padding: '28px 20px', textAlign: 'center',
            cursor: 'pointer', background: dragging ? 'var(--plum-50)' : 'var(--surface-card)', transition: 'all 0.15s',
          }}
        >
          <div style={{ marginBottom: 8, color: 'var(--text-disabled)' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 500 }}>Click or drag &amp; drop to upload</div>
          <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 4 }}>JPG, PNG, WebP, PDF</div>
          <input ref={inputRef} type="file" accept="image/*,application/pdf" style={{ display: 'none' }}
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }} />
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          {doc.preview
            ? <img src={doc.preview} alt="preview" style={{ width: 72, height: 72, objectFit: 'cover', borderRadius: 6, border: '1px solid #e5e7eb', flexShrink: 0 }} />
            : <div style={{ width: 72, height: 72, borderRadius: 6, border: '1px solid var(--border-default)', background: 'var(--status-rejected-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: 'var(--status-rejected-fg)' }}><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg></div>
          }
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#111827', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {doc.file_name}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2, marginBottom: 8 }}>
              {doc.size_kb} KB · {doc.mime_type} · <span style={{ color: 'var(--plum-500)', fontWeight: 500 }}>auto-classified by AI</span>
            </div>
            <button type="button" onClick={() => inputRef.current?.click()}
              style={{ fontSize: 12, color: 'var(--text-secondary)', background: 'var(--surface-card)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)', padding: '4px 10px', cursor: 'pointer', fontFamily: 'var(--font-ui)' }}>
              Replace
            </button>
            <input ref={inputRef} type="file" accept="image/*,application/pdf" style={{ display: 'none' }}
              onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f) }} />
          </div>
        </div>
      )}

      <div style={{ marginTop: 12 }}>
        <label style={label}>
          Patient name on document <span style={{ color: '#9ca3af', fontWeight: 400 }}>(optional)</span>
        </label>
        <input
          style={inputStyle}
          placeholder="e.g. Ravi Kumar"
          value={doc.patient_name_on_doc}
          onChange={e => onMerge({ patient_name_on_doc: e.target.value })}
        />
      </div>
    </div>
  )
}
