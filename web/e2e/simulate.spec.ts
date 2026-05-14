import { test, expect } from '@playwright/test'

// Mock backend payload — shape mirrors api.SimulateResponse so /results renders
// without hitting the FastAPI service.
const MOCK_RESPONSE = {
  result: {
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
  },
  sweet_spot: {
    milestones: [],
    sweet_spot_reason: '',
    reserve_warning: '',
    duration_months: 300,
    marginal_saving_per_1k: '0',
    effective_annual_yield: '0',
    opportunity_cost_rate: '0',
    down_payment_is_efficient: true,
    rate_floor_down_payment: '0',
    tier_economics: [],
    crossover_note: '',
  },
  schedule: null,
}

test('simulator happy path: form → results page', async ({ page }) => {
  await page.route('**/api/simulate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_RESPONSE),
    })
  })

  await page.goto('/simulate')

  await page.getByLabel(/property price/i).fill('300000')
  await page.getByLabel(/monthly net income/i).fill('4000')
  await page.getByLabel(/available savings/i).fill('80000')

  await page.getByRole('button', { name: /run simulation/i }).click()

  await expect(page).toHaveURL(/\/results$/)
  await expect(page.getByRole('heading', { name: /simulation results/i })).toBeVisible()

  // Monthly installment shown formatted as en-US
  await expect(page.getByText('€1,407.70')).toBeVisible()
})

test('simulator surfaces backend validation error', async ({ page }) => {
  await page.route('**/api/simulate', async (route) => {
    await route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Insufficient savings for any feasible plan' }),
    })
  })

  await page.goto('/simulate')
  await page.getByLabel(/property price/i).fill('500000')
  await page.getByLabel(/monthly net income/i).fill('1000')
  await page.getByLabel(/available savings/i).fill('1000')
  await page.getByRole('button', { name: /run simulation/i }).click()

  await expect(page.getByText(/insufficient savings/i)).toBeVisible()
  await expect(page).toHaveURL(/\/simulate$/)
})
