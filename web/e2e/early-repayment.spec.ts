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
