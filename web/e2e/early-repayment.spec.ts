import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
    window.localStorage.setItem('credit_simulator_tour_done', '1')
  })
})

// Mirrors the shape expected by EarlyRepaymentPanel.
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
  sweet_spot: null,
  schedule: null,
}

async function goToResults(page: import('@playwright/test').Page) {
  await page.route(/\/api\/simulate/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RESPONSE) })
  })
  await page.goto('/simulate')
  await page.locator('#property_price').fill('300000')
  await page.locator('#monthly_net_income').fill('4000')
  await page.locator('#available_savings').fill('80000')
  await page.locator('form button[type=submit]').click()
  await page.waitForURL(/\/results$/)
}

// ---------------------------------------------------------------------------
// Golden path
// ---------------------------------------------------------------------------

test('early repayment panel is visible on results page (B2)', async ({ page }) => {
  await goToResults(page)
  await expect(page.getByText('Early repayment calculator')).toBeVisible()
})

test('early repayment: compute shows summary cards', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Early repayment calculator' })
  await page.locator('#early-month').fill('60')
  await page.locator('#early-lump-sum').fill('50000')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await expect(page.getByText('Balance at repayment')).toBeVisible()
  await expect(page.getByText('New duration')).toBeVisible()
  await expect(page.getByText('Months saved')).toBeVisible()
  await expect(page.getByText('Interest saved')).toBeVisible()
})

test('early repayment: revised schedule toggle shows table', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Early repayment calculator' })
  await page.locator('#early-month').fill('60')
  await page.locator('#early-lump-sum').fill('50000')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await page.getByText('Show revised schedule').click()
  await expect(page.locator('table')).toBeVisible()
})

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

test('early repayment: invalid month shows error', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Early repayment calculator' })
  await page.locator('#early-month').fill('0')
  await page.locator('#early-lump-sum').fill('50000')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await expect(page.getByText(/Month must be between/i)).toBeVisible()
})

test('early repayment: zero lump sum shows error', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Early repayment calculator' })
  await page.locator('#early-month').fill('60')
  await page.locator('#early-lump-sum').fill('0')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await expect(page.getByText(/Enter a positive lump-sum amount/i)).toBeVisible()
})
