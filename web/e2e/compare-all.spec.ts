import { test, expect } from '@playwright/test'
import { goToResults, MOCK_ALL_PREFS_RESPONSE } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
    window.localStorage.setItem('credit_simulator_tour_done', '1')
  })
})

// Registered after goToResults so this more specific route wins for
// /api/simulate/all (Playwright matches routes newest-first).
async function mockSimulateAll(page: import('@playwright/test').Page) {
  await page.route('**/api/simulate/all', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_ALL_PREFS_RESPONSE),
    })
  })
}

test('compare-all button is visible on results page (B1)', async ({ page }) => {
  await goToResults(page)
  await expect(page.getByRole('button', { name: 'Compare all preferences' })).toBeVisible()
})

test('compare-all: clicking renders the all-preferences section', async ({ page }) => {
  await goToResults(page)
  await mockSimulateAll(page)

  await page.getByRole('button', { name: 'Compare all preferences' }).click()

  await expect(page.getByText('All-preferences comparison')).toBeVisible()

  const panel = page.locator('section').filter({ hasText: 'All-preferences comparison' })
  await expect(panel.getByRole('button', { name: 'Balanced' })).toBeVisible()
  await expect(panel.getByRole('button', { name: 'Minimize total cost' })).toBeVisible()
})

test('compare-all: infeasible preference tab is disabled', async ({ page }) => {
  await goToResults(page)
  await mockSimulateAll(page)

  await page.getByRole('button', { name: 'Compare all preferences' }).click()

  const panel = page.locator('section').filter({ hasText: 'All-preferences comparison' })
  // minimize_down_payment is null in the mock → its tab is disabled.
  await expect(panel.getByRole('button', { name: 'Minimize down payment' })).toBeDisabled()
})
