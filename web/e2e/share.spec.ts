import { test, expect } from '@playwright/test'

// Pin locale so tests don't depend on host system language.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })
})

// The share endpoint returns { id, created_at, name, result: SimulateResponse }.
// SimulateResponse wraps OptimizedResult under a nested .result key.
const MOCK_SHARED_RESPONSE = {
  id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  created_at: '2026-05-11T10:00:00+00:00',
  name: 'Brussels apartment share',
  result: {
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
  },
}

test.describe('share page (public, no auth required)', () => {
  test('renders simulation name and key metrics', async ({ page }) => {
    await page.route('**/api/share/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SHARED_RESPONSE),
      })
    })

    await page.goto('/share/test-token-abc123')

    await expect(page.getByText('Brussels apartment share')).toBeVisible()
    // Read-only badge
    await expect(page.getByText(/read-only/i)).toBeVisible()
    // Monthly installment metric
    await expect(page.getByText('€1,407.70')).toBeVisible()
    // CTA to run own simulation
    await expect(page.getByRole('link', { name: /run your own simulation/i })).toBeVisible()
  })

  test('shows not-found message for invalid or revoked token', async ({ page }) => {
    await page.route('**/api/share/**', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Shared simulation not found' }),
      })
    })

    await page.goto('/share/invalid-token-xyz')

    await expect(page.getByText(/invalid or has been revoked/i)).toBeVisible()
    await expect(page.getByRole('link', { name: /run your own simulation/i })).toBeVisible()
  })

  test('falls back to generic title when simulation has no name', async ({ page }) => {
    const unnamed = { ...MOCK_SHARED_RESPONSE, name: null }
    await page.route('**/api/share/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(unnamed),
      })
    })

    await page.goto('/share/test-token-noname')

    // Falls back to the i18n 'share.title' = "Shared simulation"
    await expect(page.getByText('Shared simulation')).toBeVisible()
  })

  test('dark mode toggle is present on share page', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('theme', 'light')
    })
    await page.route('**/api/share/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SHARED_RESPONSE),
      })
    })

    await page.goto('/share/test-token-abc123')

    await expect(page.getByRole('button', { name: 'Switch to dark mode' })).toBeVisible()
  })
})
