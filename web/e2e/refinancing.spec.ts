import { test, expect } from '@playwright/test'
import { goToResults } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
    window.localStorage.setItem('credit_simulator_tour_done', '1')
  })
})

// MOCK_RESULT's plan rate is 3.45%; a valid new rate must be 0 < r < 3.45.

// ---------------------------------------------------------------------------
// Golden path
// ---------------------------------------------------------------------------

test('refinancing panel is visible on results page (B3)', async ({ page }) => {
  await goToResults(page)
  await expect(page.getByText('Refinancing break-even')).toBeVisible()
})

test('refinancing: compute shows summary cards', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Refinancing break-even' })
  await page.locator('#refi-rate').fill('3.00')
  await page.locator('#refi-costs').fill('5000')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await expect(panel.getByText('New monthly installment')).toBeVisible()
  await expect(panel.getByText('Monthly savings')).toBeVisible()
  await expect(panel.getByText('Break-even month')).toBeVisible()
})

test('refinancing: break-even table toggle shows table', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Refinancing break-even' })
  await page.locator('#refi-rate').fill('3.00')
  await page.locator('#refi-costs').fill('5000')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await page.getByText('Show break-even table').click()
  await expect(panel.locator('table')).toBeVisible()
})

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

test('refinancing: rate at or above current rate shows error', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Refinancing break-even' })
  await page.locator('#refi-rate').fill('4.00')
  await page.locator('#refi-costs').fill('5000')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await expect(page.getByText(/must be between 0% and the current rate/i)).toBeVisible()
})

test('refinancing: negative closing costs shows error', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Refinancing break-even' })
  await page.locator('#refi-rate').fill('3.00')
  await page.locator('#refi-costs').fill('-100')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await expect(page.getByText(/non-negative closing cost/i)).toBeVisible()
})
