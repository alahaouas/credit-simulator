import { type Page } from '@playwright/test'

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
