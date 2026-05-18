import { test, expect } from '@playwright/test'
import { goToResults } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
    window.localStorage.setItem('credit_simulator_tour_done', '1')
  })
})

// ---------------------------------------------------------------------------
// Golden path
// ---------------------------------------------------------------------------

test('opportunity cost panel is visible on results page (B6)', async ({ page }) => {
  await goToResults(page)
  await expect(page.getByText('Opportunity cost')).toBeVisible()
})

test('opportunity cost: compute shows future value and gain', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Opportunity cost' })
  await page.locator('#opp-rate').fill('5')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await expect(panel.getByText('Down payment invested')).toBeVisible()
  await expect(panel.getByText('Future value')).toBeVisible()
  await expect(panel.getByText('Investment gain')).toBeVisible()
  await expect(panel.getByText('Loan interest paid')).toBeVisible()
})

test('opportunity cost: yearly growth toggle shows table', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Opportunity cost' })
  await page.locator('#opp-rate').fill('5')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await page.getByText('Show yearly growth').click()
  await expect(panel.locator('table')).toBeVisible()
})

// ---------------------------------------------------------------------------
// Validation
// ---------------------------------------------------------------------------

test('opportunity cost: zero rate shows error', async ({ page }) => {
  await goToResults(page)

  const panel = page.locator('section').filter({ hasText: 'Opportunity cost' })
  await page.locator('#opp-rate').fill('0')
  await panel.getByRole('button', { name: 'Calculate' }).click()

  await expect(page.getByText(/Enter an investment rate greater than 0/i)).toBeVisible()
})
