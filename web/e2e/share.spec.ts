import { test, expect } from '@playwright/test'
import { MOCK_SHARED_RESPONSE } from './fixtures'

// Pin locale so tests don't depend on host system language.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })
})

test.describe('share page (public, no auth required)', () => {
  test('renders simulation name and key metrics', async ({ page }) => {
    await page.route('**/api/share/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SHARED_RESPONSE),
      })
    })

    await page.goto('/share/test-token-abc123')

    await expect(page.getByText('Brussels apartment share')).toBeVisible()
    // Read-only badge
    await expect(page.getByText(/read-only/i)).toBeVisible()
    // Monthly installment metric
    await expect(page.getByText('€1,407.70')).toBeVisible()
    // CTA to run own simulation
    await expect(page.getByRole('link', { name: /run your own simulation/i })).toBeVisible()
  })

  test('shows not-found message for invalid or revoked token', async ({ page }) => {
    await page.route('**/api/share/**', async (route) => {
      await route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Shared simulation not found' }),
      })
    })

    await page.goto('/share/invalid-token-xyz')

    await expect(page.getByText(/invalid or has been revoked/i)).toBeVisible()
    await expect(page.getByRole('link', { name: /run your own simulation/i })).toBeVisible()
  })

  test('falls back to generic title when simulation has no name', async ({ page }) => {
    const unnamed = { ...MOCK_SHARED_RESPONSE, name: null }
    await page.route('**/api/share/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(unnamed),
      })
    })

    await page.goto('/share/test-token-noname')

    // Falls back to the i18n 'share.title' = "Shared simulation"
    await expect(page.getByText('Shared simulation')).toBeVisible()
  })

  test('dark mode toggle is present on share page', async ({ page }) => {
    await page.addInitScript(() => {
      window.localStorage.setItem('theme', 'light')
    })
    await page.route('**/api/share/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SHARED_RESPONSE),
      })
    })

    await page.goto('/share/test-token-abc123')

    await expect(page.getByRole('button', { name: 'Switch to dark mode' })).toBeVisible()
  })
})
