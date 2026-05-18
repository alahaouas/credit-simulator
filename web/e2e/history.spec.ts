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

// ---------------------------------------------------------------------------
// A1 — inline name / tag edit
// ---------------------------------------------------------------------------

test.describe('history inline edit (A1)', () => {
  test('Edit button shows name and tags pre-filled from the simulation', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A, SIM_B])
    await page.goto('/history')
    await expect(page.getByText('Brussels apartment')).toBeVisible()

    await page.locator('ul li').first().getByRole('button', { name: 'Edit' }).click()

    await expect(page.getByPlaceholder('Simulation name')).toHaveValue('Brussels apartment')
    // tags joined with ', '
    await expect(page.getByPlaceholder('Tags (comma-separated)')).toHaveValue('primary, 2026')
  })

  test('Cancel restores the row without changes', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A, SIM_B])
    await page.goto('/history')

    await page.locator('ul li').first().getByRole('button', { name: 'Edit' }).click()
    await expect(page.getByPlaceholder('Simulation name')).toBeVisible()

    await page.getByRole('button', { name: 'Cancel' }).first().click()

    await expect(page.getByPlaceholder('Simulation name')).not.toBeVisible()
    await expect(page.getByText('Brussels apartment')).toBeVisible()
  })

  test('Save sends PATCH and reflects updated name and tag in the list', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A, SIM_B])
    await page.route(/\/api\/simulations\/id-a$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...SIM_A, name: 'Brussels HQ', tags: ['office'] }),
      })
    })

    await page.goto('/history')
    await page.locator('ul li').first().getByRole('button', { name: 'Edit' }).click()

    await page.getByPlaceholder('Simulation name').fill('Brussels HQ')
    await page.getByPlaceholder('Tags (comma-separated)').fill('office')
    await page.getByRole('button', { name: 'Save' }).click()

    await expect(page.getByText('Brussels HQ')).toBeVisible({ timeout: 3000 })
    await expect(page.getByPlaceholder('Simulation name')).not.toBeVisible()
    await expect(page.getByText('office')).toBeVisible()
  })
})

// ---------------------------------------------------------------------------
// A2 — clone from history list
// ---------------------------------------------------------------------------

test.describe('history clone (A2)', () => {
  test('Clone navigates to /simulate with form pre-filled from saved inputs', async ({ page }) => {
    // Prevent tour from blocking form interactions on /simulate
    await page.addInitScript(() => {
      window.localStorage.setItem('credit_simulator_tour_done', '1')
    })
    await mockStats(page)
    await mockList(page, [SIM_A, SIM_B])
    await page.route(/\/api\/simulations\/id-a$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(SIM_A),
      })
    })

    await page.goto('/history')
    await expect(page.getByText('Brussels apartment')).toBeVisible()

    await page.locator('ul li').first().getByRole('button', { name: 'Clone' }).click()

    await page.waitForURL(/\/simulate/)
    await expect(page.locator('#property_price')).toHaveValue('300000')
    await expect(page.locator('#monthly_net_income')).toHaveValue('4000')
    await expect(page.locator('#available_savings')).toHaveValue('80000')
  })
})

// ---------------------------------------------------------------------------
// A5 — share generate / revoke panel
// ---------------------------------------------------------------------------

test.describe('history share panel (A5)', () => {
  test('Share button opens the panel with generate-link option when no token exists', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A])
    await page.goto('/history')

    await page.locator('ul li').first().getByRole('button', { name: 'Share' }).click()

    await expect(page.getByText('Anyone with this link can view the simulation without signing in.')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Generate public link' })).toBeVisible()
  })

  test('Generate public link shows the share URL and action buttons', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A])
    await page.route(/\/api\/simulations\/id-a\/share/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ share_token: 'tok123' }),
      })
    })

    await page.goto('/history')
    await page.locator('ul li').first().getByRole('button', { name: 'Share' }).click()
    await page.getByRole('button', { name: 'Generate public link' }).click()

    await expect(page.locator('input[readonly]')).toHaveValue(/\/share\/tok123/, { timeout: 3000 })
    await expect(page.getByRole('button', { name: 'Copy link' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Revoke' })).toBeVisible()
  })

  test('Copy link shows "Copied!" feedback', async ({ page }) => {
    // Mock clipboard so headless Chromium does not deny writeText
    await page.addInitScript(() => {
      Object.defineProperty(navigator, 'clipboard', {
        value: { writeText: async () => {} },
        configurable: true,
      })
    })
    const SIM_WITH_TOKEN = { ...SIM_A, share_token: 'tok456' }
    await mockStats(page)
    await mockList(page, [SIM_WITH_TOKEN])
    await page.goto('/history')

    await page.locator('ul li').first().getByRole('button', { name: 'Share' }).click()
    // Token already present → link input visible immediately
    await expect(page.locator('input[readonly]')).toBeVisible()
    await page.getByRole('button', { name: 'Copy link' }).click()

    await expect(page.getByRole('button', { name: 'Copied!' })).toBeVisible({ timeout: 3000 })
  })

  test('Revoke removes the share link and shows generate option again', async ({ page }) => {
    const SIM_WITH_TOKEN = { ...SIM_A, share_token: 'tok789' }
    await mockStats(page)
    await mockList(page, [SIM_WITH_TOKEN])
    await page.route(/\/api\/simulations\/id-a\/share/, async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({ status: 204 })
      }
    })

    await page.goto('/history')
    await page.locator('ul li').first().getByRole('button', { name: 'Share' }).click()
    await expect(page.getByRole('button', { name: 'Revoke' })).toBeVisible()

    await page.getByRole('button', { name: 'Revoke' }).click()

    await expect(page.getByRole('button', { name: 'Generate public link' })).toBeVisible({ timeout: 3000 })
    await expect(page.locator('input[readonly]')).not.toBeVisible()
  })

  test('Cancel closes the share panel', async ({ page }) => {
    await mockStats(page)
    await mockList(page, [SIM_A])
    await page.goto('/history')

    await page.locator('ul li').first().getByRole('button', { name: 'Share' }).click()
    await expect(page.getByText('Anyone with this link can view the simulation without signing in.')).toBeVisible()

    await page.getByRole('button', { name: 'Cancel' }).click()

    await expect(page.getByText('Anyone with this link can view the simulation without signing in.')).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Edit' })).toBeVisible()
  })
})
