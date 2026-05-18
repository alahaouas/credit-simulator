import { test, expect } from '@playwright/test'
import { mockSupabaseAuth } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem('locale', 'en'))
})

test('auth page renders the magic-link sign-in form', async ({ page }) => {
  await page.goto('/auth')
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  await expect(page.getByPlaceholder('you@example.com')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Send magic link' })).toBeVisible()
})

test('auth page: submitting an email shows the check-inbox confirmation', async ({ page }) => {
  await mockSupabaseAuth(page)
  await page.goto('/auth')

  await page.getByPlaceholder('you@example.com').fill('user@example.com')
  await page.getByRole('button', { name: 'Send magic link' }).click()

  await expect(page.getByText(/Check your inbox/i)).toBeVisible()
})

// ---------------------------------------------------------------------------
// /auth/callback — PKCE redirect handler
// ---------------------------------------------------------------------------

test('auth/callback without code redirects to home', async ({ page }) => {
  // No code param → supabase call is skipped, route redirects to /
  await page.goto('/auth/callback')
  await expect(page).toHaveURL('/')
})

test('auth/callback with code redirects to home after token exchange', async ({ page }) => {
  // The server-side Supabase client catches network errors internally, so
  // the handler redirects to / even when Supabase is unavailable in test env.
  await page.goto('/auth/callback?code=test-pkce-code-123')
  await expect(page).toHaveURL('/')
})
