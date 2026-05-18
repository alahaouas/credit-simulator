import { test, expect } from '@playwright/test'
import { injectSession, mockSupabaseAuth } from './fixtures'

const PREFS = {
  default_country: 'BE',
  default_optimization_preference: 'balanced',
  currency_display: 'symbol',
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem('locale', 'en'))
  await injectSession(page)
  await mockSupabaseAuth(page)
  await page.route('**/api/preferences', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(PREFS) })
  })
})

test('preferences page renders the form for a signed-in user (E1)', async ({ page }) => {
  await page.goto('/preferences')
  await expect(page.getByRole('heading', { name: 'Preferences' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Save' })).toBeVisible()
})

test('preferences page loads the default country from the API', async ({ page }) => {
  await page.goto('/preferences')
  // The country select is hydrated from the mocked GET /api/preferences.
  await expect(page.locator('select').first()).toHaveValue('BE')
})
