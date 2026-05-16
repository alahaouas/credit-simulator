import { test, expect } from '@playwright/test'

const TOUR_DONE_KEY = 'credit_simulator_tour_done'

// Pin locale; tour flag intentionally absent → "first visit" by default.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })
})

test.describe('onboarding tour (A7)', () => {
  test('auto-starts on first visit and shows step 1', async ({ page }) => {
    await page.goto('/simulate')
    await expect(page.getByRole('dialog', { name: 'Property price' })).toBeVisible()
    await expect(page.getByText('1 / 5')).toBeVisible()
    await expect(page.getByText('Enter the total purchase price')).toBeVisible()
  })

  test('Next button advances to step 2', async ({ page }) => {
    await page.goto('/simulate')
    await page.getByRole('button', { name: 'Next', exact: true }).click()
    await expect(page.getByRole('dialog', { name: 'Monthly net income' })).toBeVisible()
    await expect(page.getByText('2 / 5')).toBeVisible()
  })

  test('Skip dismisses the tour and sets the done flag', async ({ page }) => {
    await page.goto('/simulate')
    await page.getByRole('button', { name: 'Skip tour' }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Take tour again' })).toBeVisible()
    const flag = await page.evaluate((key) => localStorage.getItem(key), TOUR_DONE_KEY)
    expect(flag).toBe('1')
  })

  test('does not show on return visit', async ({ page }) => {
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, '1')
    }, TOUR_DONE_KEY)
    await page.goto('/simulate')
    await expect(page.getByRole('dialog')).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Take tour again' })).toBeVisible()
  })

  test('Take tour again restarts from step 1', async ({ page }) => {
    await page.addInitScript((key) => {
      window.localStorage.setItem(key, '1')
    }, TOUR_DONE_KEY)
    await page.goto('/simulate')
    await page.getByRole('button', { name: 'Take tour again' }).click()
    await expect(page.getByRole('dialog', { name: 'Property price' })).toBeVisible()
    await expect(page.getByText('1 / 5')).toBeVisible()
  })

  test('Done on the last step dismisses the tour', async ({ page }) => {
    await page.goto('/simulate')
    // Step through all 5 steps
    for (let i = 0; i < 4; i++) {
      await page.getByRole('button', { name: 'Next', exact: true }).click()
    }
    await expect(page.getByText('5 / 5')).toBeVisible()
    await page.getByRole('button', { name: 'Done' }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Take tour again' })).toBeVisible()
    const flag = await page.evaluate((key) => localStorage.getItem(key), TOUR_DONE_KEY)
    expect(flag).toBe('1')
  })
})
