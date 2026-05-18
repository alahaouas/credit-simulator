import { test, expect } from '@playwright/test'
import { goToResults, MOCK_SIMULATE_RESPONSE_WITH_SCHEDULE } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
    window.localStorage.setItem('credit_simulator_tour_done', '1')
  })
})

test('export button is visible when a schedule is present (D1)', async ({ page }) => {
  await goToResults(page, MOCK_SIMULATE_RESPONSE_WITH_SCHEDULE)
  await expect(page.getByRole('button', { name: 'Export schedule (CSV)' })).toBeVisible()
})

test('csv export: clicking export triggers a .csv download', async ({ page }) => {
  await goToResults(page, MOCK_SIMULATE_RESPONSE_WITH_SCHEDULE)

  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Export schedule (CSV)' }).click()
  const download = await downloadPromise

  expect(download.suggestedFilename()).toMatch(/^amortization_.*\.csv$/)
})

test('csv export: amortization table toggle shows the schedule table', async ({ page }) => {
  await goToResults(page, MOCK_SIMULATE_RESPONSE_WITH_SCHEDULE)

  const toggleBtn = page.getByRole('button', { name: /Show amortization schedule/i })
  await toggleBtn.scrollIntoViewIfNeeded()
  await toggleBtn.click()
  await expect(page.locator('table')).toBeVisible()
})
