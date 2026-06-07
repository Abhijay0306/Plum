import axios from 'axios'

const api = axios.create({ baseURL: '' })

export interface DocumentInput {
  file_id: string
  file_name?: string
  actual_type?: string
  quality?: string
  content?: Record<string, unknown>
  file_data?: string
  mime_type?: string
}

export interface ClaimSubmission {
  member_id: string
  policy_id: string
  claim_category: string
  treatment_date: string
  claimed_amount: number
  hospital_name?: string
  ytd_claims_amount?: number
  documents: DocumentInput[]
  simulate_component_failure?: boolean
}

export interface LineItemDecision {
  description: string
  amount: number
  approved: boolean
  approved_amount: number
  reason?: string
}

export interface FinancialBreakdown {
  claimed_amount: number
  network_discount_amount: number
  amount_after_discount: number
  copay_amount: number
  approved_amount: number
  sub_limit_cap?: number
  per_claim_cap?: number
}

export interface ClaimDecision {
  decision: 'APPROVED' | 'PARTIAL' | 'REJECTED' | 'MANUAL_REVIEW'
  approved_amount: number
  reason: string
  rejection_reasons: string[]
  line_item_decisions: LineItemDecision[]
  financial_breakdown?: FinancialBreakdown
  confidence_score: number
  degraded: boolean
  degraded_components: string[]
  manual_review_signals: string[]
  eligible_from_date?: string
}

export interface TraceCheck {
  name: string
  passed: boolean
  detail: string
}

export interface TraceEvent {
  step: number
  agent: string
  timestamp: string
  status: string
  input_summary: string
  output_summary: string
  checks: TraceCheck[]
  errors: string[]
  confidence_delta: number
  metadata: Record<string, unknown>
}

export interface ClaimResult {
  claim_id: string
  member_id: string
  policy_id: string
  claim_category: string
  claimed_amount: number
  treatment_date?: string
  hospital_name?: string
  ytd_claims_amount?: number
  decision: ClaimDecision
  trace: TraceEvent[]
  processing_time_ms: number
  created_at: string
}

export const submitClaim = (data: ClaimSubmission) =>
  api.post<ClaimResult>('/claims/submit', data).then(r => r.data)

export const listClaims = () =>
  api.get<ClaimResult[]>('/claims').then(r => r.data)

export const getClaim = (id: string) =>
  api.get<ClaimResult>(`/claims/${id}`).then(r => r.data)

export const getMembers = () =>
  api.get<Array<{ member_id: string; name: string; relationship: string }>>('/members').then(r => r.data)

export interface TestCaseMeta {
  case_id: string
  case_name: string
  description: string
  expected_decision: string | null
  expected_amount: number | null
}

export interface TestCaseResult extends ClaimResult {
  test_case: {
    case_id: string
    case_name: string
    description: string
    expected_decision: string | null
    expected_amount: number | null
    passed: boolean
    eval_notes: string[]
  }
}

export const listTestCases = () =>
  api.get<TestCaseMeta[]>('/test-cases').then(r => r.data)

export const runTestCase = (caseId: string) =>
  api.post<TestCaseResult>(`/test-cases/${caseId}/run`).then(r => r.data)

export const resubmitClaim = (claimId: string, documents: DocumentInput[]) =>
  api.post<ClaimResult>(`/claims/${claimId}/resubmit`, { documents }).then(r => r.data)
