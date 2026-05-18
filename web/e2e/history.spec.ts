import { test, expect, type Page } from '@playwright/test'
import { injectSession, mockSupabaseAuth } from './fixtures'

const MOCK_STATS = {
  total_count: 2,
  avg_monthly_installment: '1400.00',
  avg_loan_duration_months: 240,
  total_principal: '500000.00',
  avg_down_payment: '60000.00',
}
const EMPTY_STATS = {
  total_count: 0,
  avg_monthly_installment: null,
  avg_loan_duration_months: null,
  total_principal: null,
  avg_down_payment: null,
}

function makeSim(id: string, name: string, tags: string[], createdAt: string) {
  return {
    id,
    created_at: createdAt,
    name,
    tags,
    share_token: null,
    inputs: { property_price: '300000', monthly_net_income: '4000', available_savings: '80000' },
    result: { down_payment: '60000.00', loan_principal: '240000.00' },
  }
}

const SIM_A = makeSim('id-a', 'Brussels apartment', ['primary', '2026'], '2026-05-10T10:00:00+00:00')
const SIM_B = makeSim('id-b', 'Paris investment', ['rental'], '2026-05-09T10:00:00+00:00')

// Matches /api/simulations and /api/simulations?... but not /api/simulations/{id} or /stats
const LIST_ROUTE = /\/api\/simulations(?![\w/])(\?|$)/

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })

  await injectSession(page)
  await mockSupabaseAuth(page)
})

async function mockList(page: Page, items: object[], next_cursor: string | null = null) {
  await page.route(LIST_ROUTE, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items, next_cursor }),
    })
  })
}

async function mockStats(page: Page, stats = MOCK_STATS) {
  await page.route('**/api/simulations/stats', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(stats) })
  })
}

// ---------------------------------------------------------------------------
// Basic rendering
// ---------------------------------------------------------------------------

test.describe('history page (A6)', () => {
  test('renders search input', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A, SIM_B])
    await page.goto('/history')
    await expect(page.getByPlaceholder('Search by name or tag')).toBeVisible()
  })

  test('renders simulation names from API', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A, SIM_B])
    await page.goto('/history')
    await expect(page.getByText('Brussels apartment')).toBeVisible()
    await expect(page.getByText('Paris investment')).toBeVisible()
  })

  // ---------------------------------------------------------------------------
  // Empty states
  // ---------------------------------------------------------------------------

  test('shows empty-history state when no sims and no search query', async ({ page }) => {
    await mockStats(page, EMPTY_STATS)
    await mockList(page, [])
    await page.goto('/history')
    await expect(page.getByText('No saved simulations yet.')).toBeVisible()
    await expect(page.getByRole('link', { name: /run your first simulation/i })).toBeVisible()
  })

  test('shows no-results message when search returns empty', async ({ page }) => {
    await mockStats(page)
    let call = 0
    await page.route(LIST_ROUTE, async (route) => {
      call++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          call === 1
            ? { items: [SIM_A], next_cursor: null }
            : { items: [], next_cursor: null },
        ),
      })
    })

    await page.goto('/history')
    await expect(page.getByText('Brussels apartment')).toBeVisible()

    await page.getByPlaceholder('Search by name or tag').fill('zzznomatch')

    await expect(page.getByText('No simulations match your search.')).toBeVisible({ timeout: 3000 })
    await expect(page.getByRole('link', { name: /run your first simulation/i })).not.toBeVisible()
  })

  // ---------------------------------------------------------------------------
  // Pagination — Load more
  // ---------------------------------------------------------------------------

  test('Load more button is hidden when next_cursor is null', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A, SIM_B], null)
    await page.goto('/history')
    await expect(page.getByText('Brussels apartment')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Load more' })).not.toBeVisible()
  })

  test('Load more button appears when next_cursor is set', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A], '2026-05-09T10:00:00+00:00')
    await page.goto('/history')
    await expect(page.getByRole('button', { name: 'Load more' })).toBeVisible()
  })

  test('clicking Load more appends next page and hides button on last page', async ({ page }) => {
    await mockStats(page)
    let call = 0
    await page.route(LIST_ROUTE, async (route) => {
      call++
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(
          call === 1
            ? { items: [SIM_A], next_cursor: '2026-05-09T10:00:00+00:00' }
            : { items: [SIM_B], next_cursor: null },
        ),
      })
    })

    await page.goto('/history')
    await expect(page.getByText('Brussels apartment')).toBeVisible()
    await expect(page.getByText('Paris investment')).not.toBeVisible()

    await page.getByRole('button', { name: 'Load more' }).click()

    // Both items visible (appended, not replaced)
    await expect(page.getByText('Paris investment')).toBeVisible({ timeout: 3000 })
    await expect(page.getByText('Brussels apartment')).toBeVisible()
    // Button disappears on last page
    await expect(page.getByRole('button', { name: 'Load more' })).not.toBeVisible()
  })
})
