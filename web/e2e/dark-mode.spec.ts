import { test, expect } from '@playwright/test'

// Pin locale and initialise theme to light on the FIRST page load of each test.
// The conditional guard is critical: addInitScript re-runs on every full-page
// load including page.reload(), so an unconditional setItem would overwrite a
// theme that was toggled mid-test and break the "persists after reload" test.
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'en')
    if (!window.localStorage.getItem('theme')) {
      window.localStorage.setItem('theme', 'light')
    }
  })
})

test.describe('dark mode toggle', () => {
  test('toggle button is visible on the home page', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Switch to dark mode' })).toBeVisible()
  })

  test('toggle button is visible on the simulate page', async ({ page }) => {
    await page.goto('/simulate')
    await expect(page.getByRole('button', { name: 'Switch to dark mode' })).toBeVisible()
  })

  test('clicking toggle adds dark class to <html>', async ({ page }) => {
    await page.goto('/')
    await expect(page.locator('html')).not.toHaveClass(/dark/)

    await page.getByRole('button', { name: 'Switch to dark mode' }).click()

    await expect(page.locator('html')).toHaveClass(/dark/)
  })

  test('clicking toggle again removes dark class', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Switch to dark mode' }).click()
    await expect(page.locator('html')).toHaveClass(/dark/)

    await page.getByRole('button', { name: 'Switch to light mode' }).click()
    await expect(page.locator('html')).not.toHaveClass(/dark/)
  })

  test('button label reflects current theme', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: 'Switch to dark mode' })).toHaveText('Dark')

    await page.getByRole('button', { name: 'Switch to dark mode' }).click()
    await expect(page.getByRole('button', { name: 'Switch to light mode' })).toHaveText('Light')
  })

  test('preference is saved to localStorage', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Switch to dark mode' }).click()

    const stored = await page.evaluate(() => localStorage.getItem('theme'))
    expect(stored).toBe('dark')
  })

  test('dark mode persists after page reload', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Switch to dark mode' }).click()
    await expect(page.locator('html')).toHaveClass(/dark/)

    await page.reload()
    await expect(page.locator('html')).toHaveClass(/dark/)
    await expect(page.getByRole('button', { name: 'Switch to light mode' })).toBeVisible()
  })

  test('dark mode persists across navigation', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: 'Switch to dark mode' }).click()

    await page.getByRole('link', { name: /run simulation/i }).click()
    await expect(page).toHaveURL(/\/simulate$/)
    await expect(page.locator('html')).toHaveClass(/dark/)
  })
})
