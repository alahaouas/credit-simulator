import { test, expect } from '@playwright/test'
import { injectSession, mockSupabaseAuth, MOCK_SHARED_RESPONSE } from './fixtures'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem('locale', 'en'))
})

test('compare page shows a no-data message when no ids are given (A4)', async ({ page }) => {
  await page.goto('/compare')
  await expect(page.getByText(/No simulations selected/i)).toBeVisible()
})

test('compare page renders a metric table for the selected simulations', async ({ page }) => {
  await injectSession(page)
  await mockSupabaseAuth(page)

  // GET /api/simulations/{id} — echo the id so each column gets a unique key.
  await page.route('**/api/simulations/*', async (route) => {
    const id = route.request().url().split('?')[0].split('/').pop()
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ...MOCK_SHARED_RESPONSE, id, name: `Sim ${id}` }),
    })
  })

  await page.goto('/compare?ids=id-a,id-b')

  await expect(page.getByText('Metric')).toBeVisible()
  await expect(page.getByText('Down payment')).toBeVisible()
  await expect(page.getByText('Total cost')).toBeVisible()
  await expect(page.getByText('Sim id-a')).toBeVisible()
  await expect(page.getByText('Sim id-b')).toBeVisible()
})
