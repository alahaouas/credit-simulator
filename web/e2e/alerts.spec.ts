import { test, expect } from '@playwright/test'
import { injectSession, mockSupabaseAuth } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem('locale', 'en'))
})

test('alerts page prompts sign-in when not authenticated (C5)', async ({ page }) => {
  await page.goto('/alerts')
  await expect(page.getByText('Sign in to manage rate alerts.')).toBeVisible()
})

test('alerts page renders the create form for a signed-in user', async ({ page }) => {
  await injectSession(page)
  await mockSupabaseAuth(page)
  await page.route('**/api/alerts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ alerts: [] }),
    })
  })

  await page.goto('/alerts')

  await expect(page.getByRole('heading', { name: 'Rate alerts' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Add alert' })).toBeVisible()
  await expect(page.getByText('No rate alerts set.')).toBeVisible()
})

test('alerts page lists existing alerts', async ({ page }) => {
  await injectSession(page)
  await mockSupabaseAuth(page)
  await page.route('**/api/alerts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        alerts: [
          {
            id: 'a1',
            country: 'FR',
            target_rate: '0.0300',
            active: true,
            created_at: '2026-05-17T09:00:00+00:00',
            last_notified_at: null,
          },
        ],
      }),
    })
  })

  await page.goto('/alerts')

  await expect(page.getByText('FR — 3.00%')).toBeVisible()
})
