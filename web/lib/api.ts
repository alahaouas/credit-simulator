import { API_BASE } from './constants'

// All monetary/rate values are decimal strings to preserve precision.

export interface SimulateRequest {
  // Mandatory
  property_price: string
  monthly_net_income: string
  available_savings: string
  // Optional — property
  country?: string
  profile_quality?: 'average' | 'best'
  purchase_taxes?: string
  // Optional — rates
  annual_interest_rate?: string
  insurance_rate?: string
  min_down_payment_ratio?: string
  // Optional — duration
  max_loan_duration_months?: number
  fixed_loan_duration_months?: number
  // Optional — constraints
  max_debt_ratio?: string
  max_monthly_payment?: string
  preferred_down_payment?: string
  // Optional — behaviour
  optimization_preference?: string
  opportunity_cost_rate?: string
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
  period: number
  opening_balance: string
  monthly_installment: string
  principal_component: string
  interest_component: string
  insurance_component: string
  closing_balance: string
}

export interface SimulateResponse {
  result: OptimizedResult
  sweet_spot: SweetSpotAnalysis | null
  schedule: AmortizationRow[] | null
}

export interface SimulateAllResponse {
  results: Record<string, OptimizedResult | null>
}

export interface HeatmapCell {
  down_payment: string
  duration_months: number
  total_cost: string | null
  monthly_installment: string | null
}

export interface HeatmapResponse {
  cells: HeatmapCell[]
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

export async function simulateHeatmap(body: SimulateRequest): Promise<HeatmapResponse> {
  const res = await fetch(`${API_BASE}/api/simulate/heatmap`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<HeatmapResponse>
}

export async function simulateAll(
  body: SimulateRequest,
  accessToken?: string
): Promise<SimulateAllResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`

  const res = await fetch(`${API_BASE}/api/simulate/all`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }

  return res.json() as Promise<SimulateAllResponse>
}

export interface SavedSimulation {
  id: string
  created_at: string
  inputs: SimulateRequest
  name?: string | null
  tags?: string[] | null
  share_token?: string | null
}

export interface SimulationsPage {
  items: SavedSimulation[]
  next_cursor: string | null
}

export async function listSimulations(
  accessToken: string,
  params?: { search?: string; cursor?: string; limit?: number },
): Promise<SimulationsPage> {
  const qs = new URLSearchParams()
  if (params?.search) qs.set('search', params.search)
  if (params?.cursor) qs.set('cursor', params.cursor)
  if (params?.limit) qs.set('limit', String(params.limit))
  const qStr = qs.toString()
  const res = await fetch(`${API_BASE}/api/simulations${qStr ? `?${qStr}` : ''}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json()
}

export async function updateSimulationMeta(
  id: string,
  meta: { name?: string | null; tags?: string[] },
  accessToken: string
) {
  const res = await fetch(`${API_BASE}/api/simulations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(meta),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<SavedSimulation>
}

export async function getSimulation(id: string, accessToken: string) {
  const res = await fetch(`${API_BASE}/api/simulations/${id}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<{ id: string; created_at: string; name?: string | null; inputs: SimulateRequest; result: SimulateResponse }>
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

// --- Share tokens (A5) ---

export async function generateShareToken(id: string, accessToken: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/simulations/${id}/share`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  const data = await res.json()
  return data.share_token as string
}

export async function revokeShareToken(id: string, accessToken: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/simulations/${id}/share`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
}

export async function getSharedSimulation(token: string): Promise<{
  id: string
  created_at: string
  name?: string | null
  result: SimulateResponse
}> {
  const res = await fetch(`${API_BASE}/api/share/${token}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json()
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

// --- Country profiles (C1) ---

export interface LtvRateTier {
  ltv_max: string
  rate_delta: string
}

export interface CountryProfile {
  code: string
  currency: string
  annual_rate_average: string
  annual_rate_best: string
  insurance_rate_average: string
  insurance_rate_best: string
  purchase_tax_rate: string
  taxes_financeable: boolean
  min_down_payment_ratio: string
  max_debt_ratio: string
  max_loan_duration_months: number
  last_updated_date: string
  ltv_rate_tiers: LtvRateTier[]
}

export interface ProfilesResponse {
  profiles: Record<string, CountryProfile>
}

export async function listProfiles(): Promise<ProfilesResponse> {
  const res = await fetch(`${API_BASE}/api/profiles`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<ProfilesResponse>
}

export async function getProfile(country: string): Promise<CountryProfile> {
  const res = await fetch(`${API_BASE}/api/profiles/${country}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json() as Promise<CountryProfile>
}

export async function refreshRate(
  country: string,
): Promise<{ country: string; annual_rate_average: string }> {
  const res = await fetch(`${API_BASE}/api/profiles/${country}/refresh`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json()
}

// --- Rate alerts (C5) ---

export interface RateAlert {
  id: string
  country: string
  target_rate: string
  active: boolean
  created_at: string
  last_notified_at: string | null
}

export async function listAlerts(accessToken: string): Promise<{ alerts: RateAlert[] }> {
  const res = await fetch(`${API_BASE}/api/alerts`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json()
}

export async function createAlert(
  country: string,
  target_rate: string,
  accessToken: string,
): Promise<RateAlert> {
  const res = await fetch(`${API_BASE}/api/alerts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ country, target_rate }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
  return res.json()
}

export async function deleteAlert(id: string, accessToken: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/alerts/${id}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, err.detail ?? res.statusText)
  }
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
