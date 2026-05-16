import { test, expect, type Page } from '@playwright/test'

// Pin the UI locale and mark the onboarding tour as done so it doesn't
// auto-start and interfere with form interactions.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
    window.localStorage.setItem('credit_simulator_tour_done', '1')
  })
})

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
  await page.route(/\/api\/simulate/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_RESPONSE),
    })
  })

  await page.goto('/simulate')

  await page.locator('#property_price').fill('300000')
  await page.locator('#monthly_net_income').fill('4000')
  await page.locator('#available_savings').fill('80000')

  await page.locator('form button[type=submit]').click()

  await expect(page).toHaveURL(/\/results$/)
  await expect(page.locator('h1')).toBeVisible()

  // Monthly installment shown formatted as en-US
  await expect(page.getByText('€1,407.70')).toBeVisible()
})

test('simulator surfaces backend validation error', async ({ page }) => {
  await page.route(/\/api\/simulate/, async (route) => {
    await route.fulfill({
      status: 422,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Insufficient savings for any feasible plan' }),
    })
  })

  await page.goto('/simulate')
  await page.locator('#property_price').fill('500000')
  await page.locator('#monthly_net_income').fill('1000')
  await page.locator('#available_savings').fill('1000')
  await page.locator('form button[type=submit]').click()

  await expect(page.getByText(/insufficient savings/i)).toBeVisible()
  await expect(page).toHaveURL(/\/simulate$/)
})

// Tweaked response: lower rate → lower monthly installment and total cost
const MOCK_TWEAKED_RESPONSE = {
  result: {
    ...MOCK_RESPONSE.result,
    plan: {
      ...MOCK_RESPONSE.result.plan,
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

async function goToResults(page: Page) {
  let callCount = 0
  await page.route(/\/api\/simulate/, async (route) => {
    callCount++
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(callCount === 1 ? MOCK_RESPONSE : MOCK_TWEAKED_RESPONSE),
    })
  })
  await page.goto('/simulate')
  await page.locator('#property_price').fill('300000')
  await page.locator('#monthly_net_income').fill('4000')
  await page.locator('#available_savings').fill('80000')
  await page.locator('form button[type=submit]').click()
  await page.waitForURL(/\/results$/)
}

test('what-if panel is visible on results page with original values', async ({ page }) => {
  await page.route(/\/api\/simulate/, async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RESPONSE) })
  })
  await page.goto('/simulate')
  await page.locator('#property_price').fill('300000')
  await page.locator('#monthly_net_income').fill('4000')
  await page.locator('#available_savings').fill('80000')
  await page.locator('form button[type=submit]').click()
  await page.waitForURL(/\/results$/)

  await expect(page.getByText('What-if tweaking')).toBeVisible()
  await expect(page.locator('#whatif-rate')).toHaveValue('3.45')
  await expect(page.locator('#whatif-duration')).toHaveValue('300')
  // Delta table should not yet be shown (no changes made)
  await expect(page.getByText('Original')).not.toBeVisible()
})

test('what-if panel shows delta table after rate change', async ({ page }) => {
  await goToResults(page)

  await expect(page.getByText('What-if tweaking')).toBeVisible()

  // Change rate to trigger re-simulation
  await page.locator('#whatif-rate').fill('3.00')

  // Delta table should appear after debounce + API response
  await expect(page.getByText('Original')).toBeVisible({ timeout: 3000 })
  await expect(page.getByText('Tweaked')).toBeVisible()
  await expect(page.getByText('Delta')).toBeVisible()

  // Monthly installment delta cell should show a negative (green) delta
  const deltaCell = page.locator('[data-testid="whatif-delta-Monthly installment"]')
  await expect(deltaCell).toBeVisible()
  await expect(deltaCell).toHaveClass(/text-green/)
})

test('what-if reset restores original values and hides delta table', async ({ page }) => {
  await goToResults(page)

  await page.locator('#whatif-rate').fill('3.00')
  await expect(page.getByText('Original')).toBeVisible({ timeout: 3000 })

  await page.getByText('Reset').click()

  await expect(page.locator('#whatif-rate')).toHaveValue('3.45')
  await expect(page.getByText('Original')).not.toBeVisible()
})

// ---------------------------------------------------------------------------
// A2: Clone pre-fill (SESSION_CLONE_KEY → SimulatorForm hydration)
// ---------------------------------------------------------------------------

test('simulator form pre-fills from SESSION_CLONE_KEY (A2)', async ({ page }) => {
  // Land on any page to get a sessionStorage context, then write the clone key
  await page.goto('/')
  await page.evaluate(() => {
    window.sessionStorage.setItem('simulator_clone', JSON.stringify({
      property_price: '450000',
      monthly_net_income: '5500',
      available_savings: '100000',
      optimization_preference: 'minimize_total_cost',
    }))
  })

  // Navigate to /simulate — useEffect fires on mount, reads and removes the key
  await page.goto('/simulate')

  await expect(page.locator('#property_price')).toHaveValue('450000')
  await expect(page.locator('#monthly_net_income')).toHaveValue('5500')
  await expect(page.locator('#available_savings')).toHaveValue('100000')
})

test('SESSION_CLONE_KEY is removed after form hydration (A2)', async ({ page }) => {
  await page.goto('/')
  await page.evaluate(() => {
    window.sessionStorage.setItem('simulator_clone', JSON.stringify({
      property_price: '450000',
      monthly_net_income: '5500',
      available_savings: '100000',
    }))
  })

  await page.goto('/simulate')
  // After hydration the key must be gone so a subsequent reload starts fresh
  const remaining = await page.evaluate(() => window.sessionStorage.getItem('simulator_clone'))
  expect(remaining).toBeNull()
})
