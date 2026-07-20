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

test('auth page: retries once and succeeds after a transient network failure', async ({ page }) => {
  let attempts = 0
  await page.route('**/auth/v1/otp*', async (route) => {
    attempts++
    if (attempts === 1) {
      await route.abort('failed')
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: '{}',
    })
  })
  await page.goto('/auth')

  await page.getByPlaceholder('you@example.com').fill('user@example.com')
  await page.getByRole('button', { name: 'Send magic link' }).click()

  await expect(page.getByText(/Check your inbox/i)).toBeVisible()
  expect(attempts).toBe(2)
})

test('auth page: shows a timeout error after both attempts fail', async ({ page }) => {
  await page.route('**/auth/v1/otp*', async (route) => {
    await route.abort('failed')
  })
  await page.goto('/auth')

  await page.getByPlaceholder('you@example.com').fill('user@example.com')
  await page.getByRole('button', { name: 'Send magic link' }).click()

  await expect(page.getByText(/took too long/i)).toBeVisible()
})

// ---------------------------------------------------------------------------
// /auth/callback — PKCE redirect handler
// ---------------------------------------------------------------------------

test('auth/callback without code redirects to sign-in with an error', async ({ page }) => {
  // No code param → nothing to exchange → route redirects to /auth with an
  // error flag instead of silently landing on / logged out.
  await page.goto('/auth/callback')
  await expect(page).toHaveURL(/\/auth\?error=callback_failed$/)
  await expect(page.getByText(/invalid or has expired/i)).toBeVisible()
})

test('auth/callback with an invalid code redirects to sign-in with an error', async ({ page }) => {
  // No real Supabase in the test env, so the exchange always fails for a
  // fake code — the handler must redirect to /auth with an error rather
  // than pretending the sign-in succeeded.
  await page.goto('/auth/callback?code=test-pkce-code-123')
  await expect(page).toHaveURL(/\/auth\?error=callback_failed$/)
  await expect(page.getByText(/invalid or has expired/i)).toBeVisible()
})
