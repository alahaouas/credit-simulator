import { test, expect } from '@playwright/test'

// Pin the UI locale so tests don't depend on the host system language.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })
})

test.describe('home page', () => {
  test('shows title and primary CTA', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
    await expect(page.getByRole('link', { name: /run simulation|lancer une simulation/i })).toBeVisible()
  })

  test('CTA navigates to /simulate', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /run simulation|lancer une simulation/i }).click()
    await expect(page).toHaveURL(/\/simulate$/)
    await expect(page.getByRole('heading', { name: /run a simulation/i })).toBeVisible()
  })
})
