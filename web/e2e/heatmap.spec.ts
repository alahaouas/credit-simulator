import { test, expect } from '@playwright/test'
import { goToResults, MOCK_HEATMAP_RESPONSE } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
    window.localStorage.setItem('credit_simulator_tour_done', '1')
  })
})

// Registered after goToResults so this more specific route wins for
// /api/simulate/heatmap (Playwright matches routes newest-first).
async function mockHeatmap(page: import('@playwright/test').Page) {
  await page.route('**/api/simulate/heatmap', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_HEATMAP_RESPONSE),
    })
  })
}

test('heatmap panel shows load button on results page (B5)', async ({ page }) => {
  await goToResults(page)
  const panel = page.locator('section').filter({ hasText: 'Solution space heatmap' })
  await expect(panel.getByRole('button', { name: 'Show heatmap' })).toBeVisible()
})

test('heatmap: clicking Show heatmap renders the grid', async ({ page }) => {
  await goToResults(page)
  await mockHeatmap(page)

  const panel = page.locator('section').filter({ hasText: 'Solution space heatmap' })
  await panel.getByRole('button', { name: 'Show heatmap' }).click()

  // Legend appears once the grid is rendered.
  await expect(panel.getByText('Optimal point')).toBeVisible()
  await expect(panel.getByText('Infeasible')).toBeVisible()
})

test('heatmap: metric toggle switches between total cost and monthly', async ({ page }) => {
  await goToResults(page)
  await mockHeatmap(page)

  const panel = page.locator('section').filter({ hasText: 'Solution space heatmap' })
  await panel.getByRole('button', { name: 'Show heatmap' }).click()

  await expect(panel.getByRole('button', { name: 'Total cost' })).toBeVisible()
  const monthly = panel.getByRole('button', { name: 'Monthly payment' })
  await expect(monthly).toBeVisible()
  await monthly.click()
  // Toggle stays usable after switching metric.
  await expect(panel.getByRole('button', { name: 'Total cost' })).toBeVisible()
})
