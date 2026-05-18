# E2E Testing — Backlog & Improvement Plan

Audit of the Playwright e2e suite (`web/e2e/`). Use this to resume work later.

## Current state (2026-05-18)

- 18 spec files. Wired into CI (`.github/workflows/ci.yml`, `e2e` job).
- Chromium only; reports uploaded on failure; `reuseExistingServer` locally.
- Shared fixtures in `web/e2e/fixtures.ts` (mock responses, `goToResults()`,
  Supabase session injection).

## Done

- [x] **Shared fixture extraction** — `web/e2e/fixtures.ts` exports `MOCK_RESULT`,
  `MOCK_SIMULATE_RESPONSE`, `MOCK_SHARED_RESPONSE`, `MOCK_SCHEDULE`,
  `MOCK_HEATMAP_RESPONSE`, `MOCK_ALL_PREFS_RESPONSE`, `goToResults()`, and the
  Supabase auth helpers (`injectSession`, `mockSupabaseAuth`). `simulate`,
  `early-repayment`, `share`, and `history` specs import instead of duplicating.
- [x] **B6 opportunity-cost panel spec** — `opportunity-cost.spec.ts`.
- [x] **B3 refinancing break-even** — `refinancing.spec.ts`.
- [x] **B5 sweet-spot heatmap** — `heatmap.spec.ts`.
- [x] **B1 compare-all-preferences** — `compare-all.spec.ts`.
- [x] **D1 CSV export** — `csv-export.spec.ts` (download event + table toggle).
- [x] **`/compare`** (A4) — `compare.spec.ts`.
- [x] **`/rates`** (C2) — `rates.spec.ts` (render, sort toggle, refresh).
- [x] **`/preferences`** (E1) — `preferences.spec.ts`.
- [x] **`/settings`** (E3) — `settings.spec.ts`.
- [x] **`/alerts`** (C5) — `alerts.spec.ts` (signed-out + signed-in).
- [x] **`/auth`** — `auth.spec.ts` (form render + submit).
- [x] **FR locale smoke test** — `i18n-fr.spec.ts` runs the core simulate flow
  with `locale='fr'`.
- [x] **CI command** — `ci.yml` now runs `npm run test:e2e`.

## Remaining backlog

### P3 — quality / breadth

- [ ] **Selector consistency** — new tests use `getByRole` + scoped locators;
  migration of older specs' bare `getByText` calls is deferred (judgment call).
- [x] **Mobile viewport project** in `playwright.config.ts` — added `Pixel 5`
  project (`mobile-chrome`). Run with `--project=mobile-chrome` to isolate.

### Not yet covered (feature areas)

- [x] `/history` rename/tag inline edit (A1) — `history.spec.ts`
  `test.describe('history inline edit (A1)')`.
- [x] `/history` clone button (A2) — `history.spec.ts`
  `test.describe('history clone (A2)')`.
- [x] `/history` share generate/revoke panel (A5) — `history.spec.ts`
  `test.describe('history share panel (A5)')`.
- [x] C4 custom-profile section inside `SimulatorForm` — `simulate.spec.ts`
  `'C4: custom profile overrides are included in the simulate request body'`.
- [x] `/auth/callback` PKCE route — `auth.spec.ts` (no-code + code variants).
  Note: the with-code test relies on Supabase client catching its own network
  errors internally; if it starts flaking, wrap the handler in try/catch.
