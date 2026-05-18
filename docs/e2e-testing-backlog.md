# E2E Testing — Backlog & Improvement Plan

Audit of the Playwright e2e suite (`web/e2e/`). Use this to resume work later.

## Current state (2026-05-18)

- 7 spec files, ~46 tests. Wired into CI (`.github/workflows/ci.yml`, `e2e` job).
- Chromium only; reports uploaded on failure; `reuseExistingServer` locally.
- Covered: home, simulate happy-path + validation, what-if (A3), clone pre-fill
  (A2), early-repayment (B2), history search/pagination (A6), share page (A5),
  dark mode (A8), onboarding tour (A7).

## Done in this pass

- [x] **Shared fixture extraction** — `web/e2e/fixtures.ts` exports `MOCK_RESULT`,
  `MOCK_SIMULATE_RESPONSE`, `MOCK_SHARED_RESPONSE`, and the `goToResults()` helper.
  `simulate`, `early-repayment`, and `share` specs now import instead of each
  redefining a ~45-line mock object.
- [x] **B6 opportunity-cost panel spec** — `web/e2e/opportunity-cost.spec.ts`.

## Backlog

### P1 — results-page panels with no coverage

- [ ] **B3 refinancing break-even** (`RefinancingBreakEvenPanel`) — compute,
  stat cards, break-even table toggle, rate/cost validation errors.
- [ ] **B5 sweet-spot heatmap** (`SweetSpotHeatmap`) — "Show heatmap" button,
  mocked `POST /api/simulate/heatmap`, cell grid + metric toggle.
- [ ] **B1 compare-all-preferences** — "Compare all preferences" button,
  mocked `POST /api/simulate/all`, tab strip, infeasible tabs disabled.
- [ ] **D1 CSV export** — download trigger on the amortization table.

### P2 — pages with no coverage

- [ ] **`/compare`** (A4 scenario comparison) — render + parallel fetch, metric
  highlighting. Pure render, easy.
- [ ] **`/rates`** (C2 rates reference) — sortable table of country profiles,
  mocked `GET /api/profiles`. Pure render, easy.
- [ ] **`/preferences`** (E1), **`/settings`** (E3), **`/alerts`** (C5) —
  auth-gated; reuse the Supabase cookie-injection helper from `history.spec.ts`.
- [ ] **`/auth`** — magic-link login form render + submit.

### P3 — quality / breadth

- [ ] **FR locale smoke test** — every spec pins `locale='en'`; the i18n toggle
  (E2) and all French translations have no e2e safety net. Add at least one
  spec that runs a core flow with `locale='fr'`.
- [ ] **Selector consistency** — mix of `getByText` / `getByRole` / CSS `#id` /
  `data-testid`. Text selectors are brittle against copy changes. Decide on a
  convention (prefer `getByRole` + `data-testid` for dynamic values).
- [ ] **CI command** — `ci.yml` runs `npx playwright test`; project convention
  is `npm run test:e2e` from `web/`. Align for consistency.
- [ ] Consider a mobile viewport project in `playwright.config.ts` (the UI uses
  responsive grids) — low priority for a desktop-focused tool.
