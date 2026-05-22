import { test, expect } from '@playwright/test'
import {
  MOCK_SIMULATE_RESPONSE as MOCK_RESPONSE,
  MOCK_TWEAKED_RESPONSE,
  goToResults,
  seedResults,
} from './fixtures'

// Pin the UI locale and mark the onboarding tour as done so it doesn't
// auto-start and interfere with form interactions.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
    window.localStorage.setItem('credit_simulator_tour_done', '1')
  })
})

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

  await page.waitForURL(/\/results$/)
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

// ---------------------------------------------------------------------------
// What-if panel — seed results page directly from sessionStorage to skip
// the form-submit flow for tests that only care about the results page.
// ---------------------------------------------------------------------------

test('what-if panel is visible on results page with original values', async ({ page }) => {
  await seedResults(page)

  await expect(page.getByText('What-if tweaking')).toBeVisible()
  await expect(page.locator('#whatif-rate')).toHaveValue('3.45')
  await expect(page.locator('#whatif-duration')).toHaveValue('300')
  // Delta table should not yet be shown (no changes made)
  await expect(page.getByText('Original')).not.toBeVisible()
})

test('what-if panel shows delta table after rate change', async ({ page }) => {
  await page.route(/\/api\/simulate/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_TWEAKED_RESPONSE),
    })
  })
  await seedResults(page)

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
  await page.route(/\/api\/simulate/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_TWEAKED_RESPONSE),
    })
  })
  await seedResults(page)

  await page.locator('#whatif-rate').fill('3.00')
  await expect(page.getByText('Original')).toBeVisible({ timeout: 3000 })

  await page.getByText('Reset').click()

  await expect(page.locator('#whatif-rate')).toHaveValue('3.45')
  await expect(page.getByText('Original')).not.toBeVisible()
})

// ---------------------------------------------------------------------------
// A2 — Clone pre-fill (SESSION_CLONE_KEY → SimulatorForm hydration)
// ---------------------------------------------------------------------------

test('SESSION_CLONE_KEY pre-fills form and is removed after hydration (A2)', async ({ page }) => {
  // addInitScript runs before page scripts on every navigation — no need to
  // visit a throwaway page just to call sessionStorage.setItem.
  await page.addInitScript(() => {
    window.sessionStorage.setItem('simulator_clone', JSON.stringify({
      property_price: '450000',
      monthly_net_income: '5500',
      available_savings: '100000',
      optimization_preference: 'minimize_total_cost',
    }))
  })

  await page.goto('/simulate')

  await expect(page.locator('#property_price')).toHaveValue('450000')
  await expect(page.locator('#monthly_net_income')).toHaveValue('5500')
  await expect(page.locator('#available_savings')).toHaveValue('100000')
  // Key must be gone after hydration so a subsequent reload starts fresh
  const remaining = await page.evaluate(() => window.sessionStorage.getItem('simulator_clone'))
  expect(remaining).toBeNull()
})

// ---------------------------------------------------------------------------
// C4 — custom profile overrides
// ---------------------------------------------------------------------------

test('C4: custom profile overrides are included in the simulate request body', async ({ page }) => {
  let capturedBody: Record<string, unknown> | null = null

  await page.route(/\/api\/profiles\/BE/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 'BE',
        currency: '€',
        annual_rate_average: '0.0345',
        annual_rate_best: '0.0310',
        insurance_rate_average: '0.0030',
        insurance_rate_best: '0.0020',
        purchase_tax_rate: '0.12',
        taxes_financeable: false,
        min_down_payment_ratio: '0.10',
        max_debt_ratio: '0.33',
        max_loan_duration_months: 360,
        last_updated_date: '2026-05-01',
        ltv_rate_tiers: [],
      }),
    })
  })

  await page.route(/\/api\/simulate/, async (route) => {
    capturedBody = await route.request().postDataJSON()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_RESPONSE),
    })
  })

  await page.goto('/simulate')

  // Select Belgium to reveal the custom profile section
  await page.locator('#country').selectOption('BE')

  // Open the details panel first — inputs inside a closed <details> are hidden
  // by the browser regardless of DOM presence
  await page.locator('details summary').click()

  // Wait for profile loading to finish (spinner gone, inputs rendered)
  await expect(page.locator('details input[type="number"]').first()).toBeVisible({ timeout: 5000 })

  // Override the annual interest rate to 5 %
  await page.locator('details input[type="number"]').first().fill('5')

  // Fill mandatory form fields and submit
  await page.locator('#property_price').fill('300000')
  await page.locator('#monthly_net_income').fill('4000')
  await page.locator('#available_savings').fill('80000')
  await page.locator('form button[type=submit]').click()

  await page.waitForURL(/\/results$/)

  // pctToFraction('5') → '0.05'
  expect(capturedBody).not.toBeNull()
  expect((capturedBody as Record<string, unknown>).annual_interest_rate).toBe('0.05')
  expect((capturedBody as Record<string, unknown>).country).toBe('BE')
})
