import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitClaim, getMembers } from '../api/client'
import type { ClaimSubmission } from '../api/client'
import DocUploadCard, { makeEmptyDoc } from '../components/DocUploadCard'
import type { DocEntry } from '../components/DocUploadCard'

const CATEGORIES = ['CONSULTATION', 'DIAGNOSTIC', 'PHARMACY', 'DENTAL', 'VISION', 'ALTERNATIVE_MEDICINE']

const card: React.CSSProperties = {
  background: 'var(--surface-card)',
  borderRadius: 'var(--radius-xl)',
  border: '1px solid var(--border-default)',
  boxShadow: 'var(--shadow-sm)',
  padding: 28,
  marginBottom: 16,
}

const fieldLabel: React.CSSProperties = {
  display: 'block',
  fontSize: 13,
  fontWeight: 600,
  color: 'var(--text-secondary)',
  marginBottom: 6,
}

const fieldInput: React.CSSProperties = {
  width: '100%',
  padding: '9px 12px',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--border-default)',
  fontSize: 14,
  outline: 'none',
  background: 'var(--surface-card)',
  color: 'var(--text-primary)',
  boxSizing: 'border-box',
  fontFamily: 'var(--font-ui)',
  transition: 'border-color 0.15s',
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)',
      letterSpacing: '0.05em', textTransform: 'uppercase',
      marginBottom: 16, paddingBottom: 10,
      borderBottom: '1px solid var(--border-default)',
    }}>{children}</div>
  )
}

export default function SubmitClaim() {
  const navigate = useNavigate()
  const [members, setMembers] = useState<Array<{ member_id: string; name: string }>>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [form, setForm] = useState({
    member_id: 'EMP001',
    policy_id: 'PLUM_GHI_2024',
    claim_category: 'CONSULTATION',
    treatment_date: new Date().toISOString().split('T')[0],
    claimed_amount: '',
    hospital_name: '',
    ytd_claims_amount: '0',
    simulate_component_failure: false,
  })

  const [docs, setDocs] = useState<DocEntry[]>([makeEmptyDoc('doc-1')])

  useEffect(() => {
    getMembers().then(setMembers).catch(() => {})
  }, [])

  const addDoc = () => setDocs(d => [...d, makeEmptyDoc()])
  const removeDoc = (uid: string) => setDocs(d => d.filter(x => x.uid !== uid))
  const mergeDoc = (uid: string, updates: Partial<DocEntry>) =>
    setDocs(d => d.map(doc => doc.uid === uid ? { ...doc, ...updates } : doc))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.claimed_amount) return setError('Please enter a claimed amount.')
    const withFiles = docs.filter(d => d.file_data)
    if (withFiles.length === 0) return setError('Please upload at least one document.')

    setLoading(true); setError(null)
    try {
      const payload: ClaimSubmission = {
        member_id: form.member_id,
        policy_id: form.policy_id,
        claim_category: form.claim_category,
        treatment_date: form.treatment_date,
        claimed_amount: parseFloat(form.claimed_amount),
        hospital_name: form.hospital_name || undefined,
        ytd_claims_amount: parseFloat(form.ytd_claims_amount) || 0,
        simulate_component_failure: form.simulate_component_failure,
        documents: withFiles.map((d, i) => ({
          file_id: `F${String(i + 1).padStart(3, '0')}`,
          file_name: d.file_name, file_data: d.file_data, mime_type: d.mime_type,
          patient_name_on_doc: d.patient_name_on_doc || undefined,
        })),
      }
      const result = await submitClaim(payload)
      navigate(`/claims/${result.claim_id}`, { state: result })
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Submission failed. Is the backend running?')
    } finally { setLoading(false) }
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '8px 24px 64px' }}>
      <form onSubmit={handleSubmit}>
        <div style={card}>
          <SectionLabel>Claim Details</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <label style={fieldLabel}>Member</label>
              <select style={fieldInput} value={form.member_id}
                onChange={e => setForm(f => ({ ...f, member_id: e.target.value }))}>
                {members.length > 0
                  ? members.map(m => <option key={m.member_id} value={m.member_id}>{m.name} ({m.member_id})</option>)
                  : <option value="EMP001">EMP001</option>}
              </select>
            </div>
            <div>
              <label style={fieldLabel}>Claim Category</label>
              <select style={fieldInput} value={form.claim_category}
                onChange={e => setForm(f => ({ ...f, claim_category: e.target.value }))}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label style={fieldLabel}>Treatment Date</label>
              <input style={fieldInput} type="date" value={form.treatment_date}
                onChange={e => setForm(f => ({ ...f, treatment_date: e.target.value }))} />
            </div>
            <div>
              <label style={fieldLabel}>Claimed Amount (₹) <span style={{ color: 'var(--plum-500)' }}>*</span></label>
              <input style={fieldInput} type="number" placeholder="e.g. 1500" value={form.claimed_amount}
                onChange={e => setForm(f => ({ ...f, claimed_amount: e.target.value }))} />
            </div>
            <div>
              <label style={fieldLabel}>
                Hospital / Clinic <span style={{ color: 'var(--text-tertiary)', fontWeight: 400 }}>(optional)</span>
              </label>
              <input style={fieldInput} type="text" placeholder="e.g. Apollo Hospitals" value={form.hospital_name}
                onChange={e => setForm(f => ({ ...f, hospital_name: e.target.value }))} />
            </div>
            <div>
              <label style={fieldLabel}>YTD Claims Amount (₹)</label>
              <input style={fieldInput} type="number" placeholder="0" value={form.ytd_claims_amount}
                onChange={e => setForm(f => ({ ...f, ytd_claims_amount: e.target.value }))} />
            </div>
          </div>

          <div style={{ marginTop: 16, padding: '10px 14px', background: 'var(--surface-sunken)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <input type="checkbox" id="sim_fail" checked={form.simulate_component_failure}
              onChange={e => setForm(f => ({ ...f, simulate_component_failure: e.target.checked }))}
              style={{ accentColor: 'var(--plum-500)', width: 14, height: 14 }} />
            <label htmlFor="sim_fail" style={{ fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}>
              Simulate component failure <span style={{ color: 'var(--text-tertiary)' }}>— tests graceful degradation</span>
            </label>
          </div>
        </div>

        <div style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Documents
            </div>
            <button type="button" onClick={addDoc} style={{
              padding: '6px 16px', borderRadius: 999,
              border: '1.5px solid #141413',
              background: 'transparent', color: '#141413',
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
              fontFamily: 'var(--font-ui)',
            }}>+ Add Document</button>
          </div>
          <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginBottom: 16, lineHeight: 1.5 }}>
            Upload images or PDFs. The AI automatically classifies each document type.
          </p>
          {docs.map((doc, i) => (
            <DocUploadCard key={doc.uid} doc={doc} index={i}
              onRemove={() => removeDoc(doc.uid)}
              onMerge={updates => mergeDoc(doc.uid, updates)} />
          ))}
        </div>

        {error && (
          <div style={{
            background: 'var(--status-rejected-bg)',
            border: '1px solid var(--status-rejected-bd)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            marginBottom: 16,
            color: 'var(--status-rejected-fg)',
            fontSize: 13,
          }}>
            {error}
          </div>
        )}

        <button type="submit" disabled={loading} style={{
          width: '100%', padding: '14px',
          borderRadius: 'var(--radius-lg)',
          border: '1.5px solid #141413',
          background: loading ? '#D1CDC7' : '#141413',
          color: loading ? '#696969' : '#F3F0EE',
          fontWeight: 600, fontSize: 15,
          letterSpacing: '-0.01em',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontFamily: 'var(--font-ui)',
          transition: 'background 0.15s, color 0.15s',
        }}>
          {loading ? 'Processing… AI is reading your documents' : 'Submit Claim →'}
        </button>
      </form>
    </div>
  )
}
