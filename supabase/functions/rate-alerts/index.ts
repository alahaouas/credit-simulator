/**
 * C5 — Rate alert cron worker (Supabase Edge Function / Deno).
 *
 * Invoked daily by pg_cron (see setup instructions in docs/web-interface-plan.md).
 * For each active alert it:
 *   1. Fetches the current average rate for the country.
 *   2. If current rate ≤ target rate, emails the user via Resend.
 *   3. Updates last_notified_at on the alert row.
 *
 * Required env vars (set in Supabase Dashboard → Edge Functions → Secrets):
 *   RESEND_API_KEY   — Resend API key for transactional email
 *   FRED_API_KEY     — FRED API key (required for US rate fetch only)
 *   RESEND_FROM      — Sender address, e.g. "alerts@yourdomain.com"
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY') ?? ''
const FRED_API_KEY = Deno.env.get('FRED_API_KEY') ?? ''
const RESEND_FROM = Deno.env.get('RESEND_FROM') ?? 'alerts@creditsimulator.app'

const ECB_COUNTRIES = new Set(['FR', 'DE', 'ES', 'IT', 'PT'])

// ---------------------------------------------------------------------------
// Rate fetchers (mirrors Python fetcher.py logic)
// ---------------------------------------------------------------------------

async function fetchEcbRate(country: string): Promise<number> {
  const url =
    `https://data.ecb.europa.eu/api/v1/data/MIR/` +
    `M.${country}.B.A2C.F.R.A.2250.EUR.N?lastNObservations=1&format=jsondata`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`ECB API error ${res.status} for ${country}`)
  const data = await res.json()
  const series = data.dataSets[0].series
  const seriesKey = Object.keys(series)[0]
  const observations = series[seriesKey].observations
  const obsKey = Object.keys(observations)[0]
  const value = observations[obsKey][0]
  if (value === null) throw new Error(`ECB returned null for ${country}`)
  return value / 100
}

async function fetchBoeRate(): Promise<number> {
  const url =
    'https://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp' +
    '?csv.x=yes&Datefrom=01/Jan/2024&Dateto=now&SeriesCodes=IUMTLMV&CSVF=TT&UsingCodes=Y'
  const res = await fetch(url)
  if (!res.ok) throw new Error(`BoE API error ${res.status}`)
  const text = await res.text()
  const lines = text.trim().split('\n')
  if (lines.length < 2) throw new Error('No BoE data returned')
  const header = lines[0].split(',').map((h: string) => h.trim())
  const rateCol = header.indexOf('IUMTLMV')
  if (rateCol < 0) throw new Error('IUMTLMV column not found in BoE CSV')
  let lastValue: string | null = null
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(',')
    if (parts.length > rateCol && parts[rateCol].trim()) {
      lastValue = parts[rateCol].trim()
    }
  }
  if (!lastValue) throw new Error('No rate data in BoE response')
  return parseFloat(lastValue) / 100
}

async function fetchFredRate(): Promise<number> {
  if (!FRED_API_KEY) throw new Error('FRED_API_KEY not configured')
  const url =
    `https://api.stlouisfed.org/fred/series/observations` +
    `?series_id=MORTGAGE30US&api_key=${FRED_API_KEY}&file_type=json&sort_order=desc&limit=1`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`FRED API error ${res.status}`)
  const data = await res.json()
  const value = data.observations?.[0]?.value
  if (!value || value === '.') throw new Error('FRED returned no data')
  return parseFloat(value) / 100
}

async function fetchRate(country: string): Promise<number | null> {
  try {
    if (ECB_COUNTRIES.has(country)) return await fetchEcbRate(country)
    if (country === 'GB') return await fetchBoeRate()
    if (country === 'US') return await fetchFredRate()
    return null // BE and any future countries without an online source
  } catch (err) {
    console.error(`Rate fetch failed for ${country}:`, err)
    return null
  }
}

// ---------------------------------------------------------------------------
// Email via Resend
// ---------------------------------------------------------------------------

async function sendEmail(
  to: string,
  country: string,
  targetRate: number,
  currentRate: number,
): Promise<void> {
  if (!RESEND_API_KEY) {
    console.warn('RESEND_API_KEY not set — skipping email to', to)
    return
  }
  const targetPct = (targetRate * 100).toFixed(2)
  const currentPct = (currentRate * 100).toFixed(2)
  await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${RESEND_API_KEY}`,
    },
    body: JSON.stringify({
      from: RESEND_FROM,
      to: [to],
      subject: `Rate alert: ${country} mortgage rate is now ${currentPct}%`,
      text: [
        `Your rate alert for ${country} has been triggered.`,
        '',
        `Current rate : ${currentPct}%`,
        `Your target  : ${targetPct}%`,
        '',
        'Log in to Credit Simulator to run a new simulation with the updated rate.',
      ].join('\n'),
    }),
  })
}

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------

Deno.serve(async (_req: Request) => {
  const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

  const { data: alerts, error } = await supabase
    .from('rate_alerts')
    .select('id, user_id, country, target_rate')
    .eq('active', true)

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  if (!alerts || alerts.length === 0) {
    return new Response(JSON.stringify({ triggered: 0, checked: 0 }), {
      headers: { 'Content-Type': 'application/json' },
    })
  }

  // Fetch each unique country's rate once
  const countries = [...new Set(alerts.map((a: { country: string }) => a.country))]
  const rates: Record<string, number | null> = {}
  for (const country of countries) {
    rates[country] = await fetchRate(country)
  }

  let triggered = 0
  for (const alert of alerts) {
    const currentRate = rates[alert.country]
    if (currentRate === null) continue
    if (currentRate > parseFloat(alert.target_rate)) continue

    const { data: { user } } = await supabase.auth.admin.getUserById(alert.user_id)
    if (!user?.email) continue

    await sendEmail(user.email, alert.country, parseFloat(alert.target_rate), currentRate)
    await supabase
      .from('rate_alerts')
      .update({ last_notified_at: new Date().toISOString() })
      .eq('id', alert.id)

    triggered++
  }

  return new Response(JSON.stringify({ triggered, checked: alerts.length }), {
    headers: { 'Content-Type': 'application/json' },
  })
})
