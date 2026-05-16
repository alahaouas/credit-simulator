import * as fs from 'fs'
import * as path from 'path'
import { test, expect, type Page } from '@playwright/test'

// ---------------------------------------------------------------------------
// Supabase cookie name — computed once at module load in Node.js context.
// @supabase/ssr derives the cookie name as `sb-{hostname-first-segment}-auth-token`
// from NEXT_PUBLIC_SUPABASE_URL. We read it from the test process env first,
// then fall back to parsing .env.local, then fall back to the local Supabase
// default so CI and worktrees without .env.local still work.
// ---------------------------------------------------------------------------
function resolveSupabaseUrl(): string {
  if (process.env.NEXT_PUBLIC_SUPABASE_URL) return process.env.NEXT_PUBLIC_SUPABASE_URL
  try {
    const envPath = path.join(__dirname, '..', '.env.local')
    const content = fs.readFileSync(envPath, 'utf8')
    const match = content.match(/^NEXT_PUBLIC_SUPABASE_URL=(.+)$/m)
    if (match) return match[1].trim()
  } catch { /* no .env.local */ }
  return 'http://localhost:54321'
}

const SUPABASE_URL = resolveSupabaseUrl()
const SUPABASE_REF = new URL(SUPABASE_URL).hostname.split('.')[0]
const SESSION_COOKIE_NAME = `sb-${SUPABASE_REF}-auth-token`

const FAKE_SESSION = {
  access_token: 'fake-access-token',
  token_type: 'bearer',
  expires_in: 3600,
  // Far-future expiry so auth-js never tries to refresh
  expires_at: Math.floor(Date.now() / 1000) + 86400,
  refresh_token: 'fake-refresh-token',
  user: { id: 'test-user-id', email: 'test@example.com', role: 'authenticated' },
}

// @supabase/ssr v0.10 stores sessions as `base64-{base64url(JSON.stringify(session))}` in cookies.
// Using Node.js Buffer to produce the same encoding.
const SESSION_COOKIE_VALUE =
  'base64-' +
  Buffer.from(JSON.stringify(FAKE_SESSION))
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')

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

// Cookie name and value are fully computed in Node.js — no page navigation needed.
async function injectSession(page: Page) {
  await page.context().addCookies([
    { name: SESSION_COOKIE_NAME, value: SESSION_COOKIE_VALUE, domain: 'localhost', path: '/' },
  ])
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
  })

  await injectSession(page)

  // Intercept Supabase token-refresh calls that the middleware or auth-js may make
  await page.route('**/auth/v1/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'fake-access-token',
        token_type: 'bearer',
        expires_in: 3600,
        user: { id: 'test-user-id', email: 'test@example.com' },
      }),
    })
  })
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
