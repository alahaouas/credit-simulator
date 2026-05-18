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
