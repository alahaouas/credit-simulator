import { test, expect } from '@playwright/test'
import { injectSession, mockSupabaseAuth } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem('locale', 'en'))
  await injectSession(page)
  await mockSupabaseAuth(page)
})

test('settings page renders the API keys UI for a signed-in user (E3)', async ({ page }) => {
  await page.route('**/api/keys', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
  })
  await page.goto('/settings')

  await expect(page.getByRole('heading', { name: 'API Keys' })).toBeVisible()
  await expect(page.getByText('No API keys yet.')).toBeVisible()
})

test('settings page lists existing API keys', async ({ page }) => {
  const KEYS = [
    {
      id: 'k1',
      name: 'my-script',
      key_prefix: 'csim_ab12cd',
      created_at: '2026-05-14T10:00:00+00:00',
      last_used_at: null,
    },
  ]
  await page.route('**/api/keys', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(KEYS) })
  })
  await page.goto('/settings')

  await expect(page.getByText('my-script')).toBeVisible()
})
