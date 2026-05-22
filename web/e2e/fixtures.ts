import * as fs from 'fs'
import * as path from 'path'
import { expect, type Page } from '@playwright/test'

// Canonical OptimizedResult used across results-page specs. Shape mirrors
// api.OptimizedResult so /results renders without hitting the FastAPI service.
export const MOCK_RESULT = {
  down_payment: '60000.00',
  loan_principal: '268800.00',
  loan_duration_months: 300,
  ltv_ratio: '0.8960',
  country: 'BE',
  profile_quality: 'average',
  currency: '€',
  monthly_net_income: '4000',
  property_price: '300000',
  purchase_taxes: '36000.00',
  total_acquisition_cost: '328800.00',
  optimization_preference: 'balanced',
  parameters_source: {},
  plan: {
    loan_principal: '268800.00',
    annual_interest_rate: '0.0345',
    annual_insurance_rate: '0.0030',
    loan_duration_months: 300,
    monthly_emi: '1340.50',
    monthly_insurance: '67.20',
    monthly_installment: '1407.70',
    monthly_interest_first: '772.80',
    total_interest_paid: '133350.00',
    total_insurance_paid: '20160.00',
    total_cost_of_credit: '153510.00',
    total_repaid: '422310.00',
    effective_annual_rate: '0.0387',
  },
}

// Full POST /api/simulate response envelope.
export const MOCK_SIMULATE_RESPONSE = {
  result: MOCK_RESULT,
  sweet_spot: null,
  schedule: null,
}

// GET /api/share/{token} response — wraps a SimulateResponse under .result.
export const MOCK_SHARED_RESPONSE = {
  id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  created_at: '2026-05-11T10:00:00+00:00',
  name: 'Brussels apartment share',
  result: {
    result: MOCK_RESULT,
    sweet_spot: null,
    schedule: null,
  },
}

// A short amortization schedule (api.AmortizationRow[]) for CSV-export tests.
export const MOCK_SCHEDULE = [
  {
    period: 1,
    opening_balance: '268800.00',
    monthly_installment: '1407.70',
    principal_component: '568.50',
    interest_component: '772.80',
    insurance_component: '67.20',
    closing_balance: '268231.50',
  },
  {
    period: 2,
    opening_balance: '268231.50',
    monthly_installment: '1407.70',
    principal_component: '570.13',
    interest_component: '771.17',
    insurance_component: '67.20',
    closing_balance: '267661.37',
  },
  {
    period: 3,
    opening_balance: '267661.37',
    monthly_installment: '1407.70',
    principal_component: '571.77',
    interest_component: '769.53',
    insurance_component: '67.20',
    closing_balance: '267089.60',
  },
]

// POST /api/simulate response that includes a schedule (for CSV-export tests).
export const MOCK_SIMULATE_RESPONSE_WITH_SCHEDULE = {
  result: MOCK_RESULT,
  sweet_spot: null,
  schedule: MOCK_SCHEDULE,
}

// POST /api/simulate/heatmap response. The (60000, 300) cell matches
// MOCK_RESULT's optimal point; the (80000, 300) cell is infeasible (null).
export const MOCK_HEATMAP_RESPONSE = {
  cells: [
    { down_payment: '40000.00', duration_months: 240, total_cost: '150000.00', monthly_installment: '1500.00' },
    { down_payment: '40000.00', duration_months: 300, total_cost: '160000.00', monthly_installment: '1300.00' },
    { down_payment: '60000.00', duration_months: 240, total_cost: '140000.00', monthly_installment: '1450.00' },
    { down_payment: '60000.00', duration_months: 300, total_cost: '153510.00', monthly_installment: '1407.70' },
    { down_payment: '80000.00', duration_months: 240, total_cost: '130000.00', monthly_installment: '1400.00' },
    { down_payment: '80000.00', duration_months: 300, total_cost: null, monthly_installment: null },
  ],
}

// POST /api/simulate/all response — minimize_down_payment is infeasible (null).
export const MOCK_ALL_PREFS_RESPONSE = {
  results: {
    balanced: MOCK_RESULT,
    minimize_total_cost: MOCK_RESULT,
    minimize_monthly_payment: MOCK_RESULT,
    minimize_duration: MOCK_RESULT,
    minimize_down_payment: null,
  },
}

// Minimal SimulateRequest matching MOCK_RESULT's user inputs.
export const MOCK_INPUTS = {
  property_price: '300000',
  monthly_net_income: '4000',
  available_savings: '80000',
}

// Lower-rate variant returned on what-if re-simulation.
export const MOCK_TWEAKED_RESPONSE = {
  result: {
    ...MOCK_RESULT,
    plan: {
      ...MOCK_RESULT.plan,
      annual_interest_rate: '0.0300',
      monthly_emi: '1270.00',
      monthly_installment: '1337.20',
      total_interest_paid: '112600.00',
      total_cost_of_credit: '132760.00',
    },
  },
  sweet_spot: null,
  schedule: null,
}

// Seed the results page from sessionStorage and navigate directly to /results,
// bypassing the form submit flow entirely. Faster than goToResults for tests
// that only care about the results page state.
export async function seedResults(page: Page) {
  const payload = { result: MOCK_SIMULATE_RESPONSE, inputs: MOCK_INPUTS }
  await page.addInitScript((data) => {
    window.sessionStorage.setItem('simulator_result', JSON.stringify(data.result))
    window.sessionStorage.setItem('simulator_inputs', JSON.stringify(data.inputs))
  }, payload)
  await page.goto('/results')
  await expect(page.locator('h1')).toBeVisible()
}

// Fill the simulator form and land on /results with a mocked /api/simulate.
export async function goToResults(
  page: Page,
  response: unknown = MOCK_SIMULATE_RESPONSE,
) {
  await page.route(/\/api\/simulate/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(response),
    })
  })
  await page.goto('/simulate')
  await page.locator('#property_price').fill('300000')
  await page.locator('#monthly_net_income').fill('4000')
  await page.locator('#available_savings').fill('80000')
  await page.locator('form button[type=submit]').click()
  await page.waitForURL(/\/results$/)
}

// ---------------------------------------------------------------------------
// Supabase auth — fake session injection for auth-gated page specs.
//
// @supabase/ssr derives the cookie name as `sb-{hostname-first-segment}-auth-token`
// from NEXT_PUBLIC_SUPABASE_URL. We resolve the URL from the test process env
// first, then parse web/.env.local, then fall back to the local Supabase default
// so CI and worktrees without .env.local still work.
// ---------------------------------------------------------------------------

function resolveSupabaseUrl(): string {
  if (process.env.NEXT_PUBLIC_SUPABASE_URL) return process.env.NEXT_PUBLIC_SUPABASE_URL
  try {
    const envPath = path.join(__dirname, '..', '.env.local')
    const content = fs.readFileSync(envPath, 'utf8')
    const match = content.match(/^NEXT_PUBLIC_SUPABASE_URL=(.+)$/m)
    if (match) return match[1].trim()
  } catch { /* no .env.local */ }
  return 'http://localhost:54321'
}

const SUPABASE_REF = new URL(resolveSupabaseUrl()).hostname.split('.')[0]
export const SESSION_COOKIE_NAME = `sb-${SUPABASE_REF}-auth-token`

const FAKE_SESSION = {
  access_token: 'fake-access-token',
  token_type: 'bearer',
  expires_in: 3600,
  // Far-future expiry so auth-js never tries to refresh.
  expires_at: Math.floor(Date.now() / 1000) + 86400,
  refresh_token: 'fake-refresh-token',
  user: { id: 'test-user-id', email: 'test@example.com', role: 'authenticated' },
}

// @supabase/ssr v0.10 stores sessions as `base64-{base64url(JSON.stringify(session))}`.
export const SESSION_COOKIE_VALUE =
  'base64-' +
  Buffer.from(JSON.stringify(FAKE_SESSION))
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')

// Inject a fake Supabase session cookie so auth-gated pages render as signed-in.
export async function injectSession(page: Page) {
  await page.context().addCookies([
    { name: SESSION_COOKIE_NAME, value: SESSION_COOKIE_VALUE, domain: 'localhost', path: '/' },
  ])
}

// Stub Supabase token-refresh calls the middleware / auth-js may make.
export async function mockSupabaseAuth(page: Page) {
  await page.route('**/auth/v1/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'fake-access-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: { id: 'test-user-id', email: 'test@example.com' },
      }),
    })
  })
}
