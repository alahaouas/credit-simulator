const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// All monetary/rate values are decimal strings to preserve precision.

export interface SimulateRequest {
  // Mandatory
  property_price: string
  monthly_net_income: string
  available_savings: string
  // Optional — property
  country?: string
  profile_quality?: string
  purchase_taxes?: string
  loan_duration_months?: number
  // Optional — rates
  annual_interest_rate?: string
  insurance_rate?: string
  min_down_payment_ratio?: string
  // Optional — constraints
  max_debt_ratio?: string
  max_monthly_payment?: string
  preferred_down_payment?: string
  // Optional — behaviour
  optimization_preference?: string
  opportunity_cost_rate?: string
  locale?: string
  // Optional — output
  include_schedule?: boolean
  include_sweet_spot?: boolean
}

export interface LoanPlan {
  loan_principal: string
  annual_interest_rate: string
  annual_insurance_rate: string
  loan_duration_months: number
  monthly_emi: string
  monthly_insurance: string
  monthly_installment: string
  monthly_interest_first: string
  total_interest_paid: string
  total_insurance_paid: string
  total_cost_of_credit: string
  total_repaid: string
  effective_annual_rate: string
}

export interface OptimizedResult {
  down_payment: string
  loan_principal: string
  loan_duration_months: number
  ltv_ratio: string
  country: string
  profile_quality: string
  currency: string
  monthly_net_income: string
  property_price: string
  purchase_taxes: string
  total_acquisition_cost: string
  optimization_preference: string
  parameters_source: Record<string, string>
  plan: LoanPlan
}

export interface SweetSpotMilestone {
  down_payment: string
  label: string
  monthly_installment: string
  total_cost_of_credit: string
  opportunity_cost: string
  net_saving_vs_previous: string
  ltv_ratio: string
  rate: string
}

export interface SweetSpotAnalysis {
  milestones: SweetSpotMilestone[]
  sweet_spot_reason: string
  reserve_warning: string
  duration_months: number
  marginal_saving_per_1k: string
  effective_annual_yield: string
  opportunity_cost_rate: string
  down_payment_is_efficient: boolean
  rate_floor_down_payment: string
  tier_economics: unknown[]
  crossover_note: string
}

export interface AmortizationRow {
  month: number
  opening_balance: string
  emi: string
  interest: string
  principal: string
  insurance: string
  total_payment: string
  closing_balance: string
}

export interface SimulateResponse {
  result: OptimizedResult
  sweet_spot: SweetSpotAnalysis | null
  schedule: AmortizationRow[] | null
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function simulate(
  body: SimulateRequest,
  accessToken?: string
): Promise<SimulateResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`

  const res = await fetch(`${API_BASE}/api/simulate`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }

  return res.json() as Promise<SimulateResponse>
}

export async function listSimulations(accessToken: string) {
  const res = await fetch(`${API_BASE}/api/simulations`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<Array<{ id: string; created_at: string; inputs: SimulateRequest }>>
}

export async function getSimulation(id: string, accessToken: string) {
  const res = await fetch(`${API_BASE}/api/simulations/${id}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<{ id: string; created_at: string; inputs: SimulateRequest; result: SimulateResponse }>
}

export async function deleteSimulation(id: string, accessToken: string) {
  const res = await fetch(`${API_BASE}/api/simulations/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
}

// --- Simulation stats (E4) ---

export interface SimulationStats {
  total_count: number
  avg_monthly_installment: string | null
  avg_loan_duration_months: number | null
  total_principal: string | null
  avg_down_payment: string | null
}

export async function getSimulationStats(accessToken: string): Promise<SimulationStats> {
  const res = await fetch(`${API_BASE}/api/simulations/stats`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<SimulationStats>
}

// --- User preferences (E1) ---

export interface UserPreferences {
  default_country: string
  default_optimization_preference: string
  currency_display: 'symbol' | 'code'
}

export async function getPreferences(accessToken: string): Promise<UserPreferences> {
  const res = await fetch(`${API_BASE}/api/preferences`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<UserPreferences>
}

export async function updatePreferences(
  prefs: Partial<UserPreferences>,
  accessToken: string
): Promise<UserPreferences> {
  const res = await fetch(`${API_BASE}/api/preferences`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(prefs),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<UserPreferences>
}

// --- API keys (E3) ---

export interface ApiKey {
  id: string
  name: string
  key_prefix: string
  created_at: string
  last_used_at: string | null
}

export interface CreatedApiKey extends ApiKey {
  key: string
}

export async function listApiKeys(accessToken: string): Promise<ApiKey[]> {
  const res = await fetch(`${API_BASE}/api/keys`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<ApiKey[]>
}

export async function createApiKey(name: string, accessToken: string): Promise<CreatedApiKey> {
  const res = await fetch(`${API_BASE}/api/keys`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<CreatedApiKey>
}

export async function deleteApiKey(id: string, accessToken: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/keys/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
}
