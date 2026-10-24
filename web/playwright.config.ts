import { defineConfig, devices } from '@playwright/test'

const PORT = process.env.PORT ?? '3000'
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? `http://localhost:${PORT}`

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: { args: ['--disable-web-security'] },
      },
    },
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
        launchOptions: { args: ['--disable-web-security'] },
      },
    },
  ],
  webServer: {
    // CI tests a production build: `next dev` compiles each route on its first visit,
    // which made the suite ~3x slower (161 s vs 39-52 s of tests, measured 2026-10-24).
    // Workers stay at Playwright's default (2 on the 4-vCPU runner): 4 was no faster.
    command: process.env.CI ? 'npm run build && npm run start' : 'npm run dev',
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 240_000,
    // Provide dummy Supabase credentials so the dev server starts cleanly in
    // CI (no .env.local). In local dev, reuseExistingServer is true so the
    // already-running server's real env vars are used instead.
    env: {
      NEXT_PUBLIC_SUPABASE_URL:
        process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'http://localhost:54321',
      NEXT_PUBLIC_SUPABASE_ANON_KEY:
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRFA0NiK7urOEB8p5gPNu5LKTH5psBMNFNuvQmLlC7c',
    },
  },
})
