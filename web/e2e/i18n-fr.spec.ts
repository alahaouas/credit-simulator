import { test, expect } from '@playwright/test'
import { goToResults } from './fixtures'

// Every other spec pins locale='en'. This one exercises a core flow in French
// so the FR translations and the i18n toggle (E2) have e2e coverage.
test('core simulate flow renders in French (E2)', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('locale', 'fr')
    window.localStorage.setItem('credit_simulator_tour_done', '1')
  })

  // goToResults uses id/type selectors, so it is locale-independent.
  await goToResults(page)

  await expect(page.getByRole('heading', { name: 'Résultats de la simulation' })).toBeVisible()
})
