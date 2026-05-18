import { test, expect } from '@playwright/test'

// GET /api/profiles response — two countries so sort order is observable.
const PROFILES = {
  profiles: {
    BE: {
      code: 'BE', currency: 'EUR',
      annual_rate_average: '0.0340', annual_rate_best: '0.0320',
      insurance_rate_average: '0.0020', insurance_rate_best: '0.0015',
      purchase_tax_rate: '0.1250', taxes_financeable: true,
      min_down_payment_ratio: '0.2000', max_debt_ratio: '0.3500',
      max_loan_duration_months: 300, last_updated_date: '2026-05', ltv_rate_tiers: [],
    },
    FR: {
      code: 'FR', currency: 'EUR',
      annual_rate_average: '0.0350', annual_rate_best: '0.0290',
      insurance_rate_average: '0.0030', insurance_rate_best: '0.0010',
      purchase_tax_rate: '0.0750', taxes_financeable: false,
      min_down_payment_ratio: '0.0000', max_debt_ratio: '0.3500',
      max_loan_duration_months: 300, last_updated_date: '', ltv_rate_tiers: [],
    },
  },
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem('locale', 'en'))
  await page.route('**/api/profiles', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PROFILES) })
  })
})

test('rates page renders a row per country (C2)', async ({ page }) => {
  await page.goto('/rates')
  await expect(page.getByRole('heading', { name: 'Rates reference' })).toBeVisible()
  await expect(page.locator('tbody tr')).toHaveCount(2)
})

test('rates page: clicking a column header toggles sort order', async ({ page }) => {
  await page.goto('/rates')
  const firstCode = page.locator('tbody tr').first().locator('td').first()
  await expect(firstCode).toHaveText('BE') // default: code ascending
  await page.getByRole('columnheader', { name: /Country/ }).click()
  await expect(firstCode).toHaveText('FR') // toggled to descending
})

test('rates page: refreshing a country updates its average rate', async ({ page }) => {
  await page.route('**/api/profiles/*/refresh', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ country: 'BE', annual_rate_average: '0.0299' }),
    })
  })
  await page.goto('/rates')
  await page.getByRole('button', { name: 'Refresh' }).first().click()
  await expect(page.getByText('2.99%')).toBeVisible()
})
