'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import { getSimulation, ApiError, OptimizedResult, LoanPlan } from '@/lib/api'
import { useI18n, type TranslationKey } from '@/lib/i18n'
import { DarkModeToggle } from '@/components/DarkModeToggle'
import { LocaleToggle } from '@/components/LocaleToggle'

type FullSim = {
  id: string
  created_at: string
  name?: string | null
  result: OptimizedResult
  plan: LoanPlan
}

type MetricDef = {
  key: string
  labelKey: TranslationKey
  getValue: (s: FullSim) => number
  format: (n: number, currency: string) => string
  lowerIsBetter: boolean
}

function fmtCurrency(n: number, currency: string) {
  return `${currency}${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtPct(n: number) {
  return `${n.toFixed(3)} %`
}

function fmtMonths(n: number) {
  return `${n} mo`
}

const METRICS: MetricDef[] = [
  {
    key: 'down_payment',
    labelKey: 'compare.down_payment',
    getValue: s => parseFloat(s.result.down_payment),
    format: (n, c) => fmtCurrency(n, c),
    lowerIsBetter: false,
  },
  {
    key: 'loan_principal',
    labelKey: 'compare.loan_principal',
    getValue: s => parseFloat(s.result.loan_principal),
    format: (n, c) => fmtCurrency(n, c),
    lowerIsBetter: true,
  },
  {
    key: 'duration',
    labelKey: 'compare.duration',
    getValue: s => s.result.loan_duration_months,
    format: n => fmtMonths(n),
    lowerIsBetter: true,
  },
  {
    key: 'monthly',
    labelKey: 'compare.monthly',
    getValue: s => parseFloat(s.plan.monthly_installment),
    format: (n, c) => fmtCurrency(n, c),
    lowerIsBetter: true,
  },
  {
    key: 'rate',
    labelKey: 'compare.rate',
    getValue: s => parseFloat(s.plan.annual_interest_rate),
    format: n => fmtPct(n),
    lowerIsBetter: true,
  },
  {
    key: 'total_interest',
    labelKey: 'compare.total_interest',
    getValue: s => parseFloat(s.plan.total_interest_paid),
    format: (n, c) => fmtCurrency(n, c),
    lowerIsBetter: true,
  },
  {
    key: 'total_cost',
    labelKey: 'compare.total_cost',
    getValue: s => parseFloat(s.plan.total_cost_of_credit),
    format: (n, c) => fmtCurrency(n, c),
    lowerIsBetter: true,
  },
  {
    key: 'apr',
    labelKey: 'compare.apr',
    getValue: s => parseFloat(s.plan.effective_annual_rate),
    format: n => fmtPct(n),
    lowerIsBetter: true,
  },
  {
    key: 'ltv',
    labelKey: 'compare.ltv',
    getValue: s => parseFloat(s.result.ltv_ratio),
    format: n => fmtPct(n),
    lowerIsBetter: true,
  },
]

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function CompareTable({ sims }: { sims: FullSim[] }) {
  const { t } = useI18n()
  const currency = sims[0]?.result.currency ?? '€'

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr>
            <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-gray-400 border-b dark:border-gray-700 w-40">
              {t('compare.metric_col')}
            </th>
            {sims.map((s, i) => (
              <th
                key={s.id}
                className="text-left px-4 py-3 font-semibold border-b dark:border-gray-700"
              >
                <span className="block">{s.name ?? `#${i + 1}`}</span>
                <span className="block text-xs font-normal text-gray-400 dark:text-gray-500 mt-0.5">
                  {formatDate(s.created_at)}
                </span>
                <span className="block text-xs font-normal text-gray-500 dark:text-gray-400">
                  {s.result.country} · {s.result.optimization_preference}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {METRICS.map(metric => {
            const values = sims.map(s => metric.getValue(s))
            const best = metric.lowerIsBetter ? Math.min(...values) : null
            return (
              <tr key={metric.key} className="border-b dark:border-gray-700 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                <td className="px-4 py-3 text-gray-600 dark:text-gray-400 font-medium whitespace-nowrap">
                  {t(metric.labelKey)}
                </td>
                {sims.map((s, i) => {
                  const val = values[i]
                  const isBest = best !== null && val === best && values.filter(v => v === best).length < sims.length
                  return (
                    <td
                      key={s.id}
                      className={`px-4 py-3 tabular-nums ${isBest ? 'text-green-600 dark:text-green-400 font-semibold' : ''}`}
                    >
                      {metric.format(val, currency)}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function CompareInner() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { t } = useI18n()
  const [sims, setSims] = useState<FullSim[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const rawIds = searchParams.get('ids') ?? ''
    const ids = rawIds.split(',').map(s => s.trim()).filter(Boolean).slice(0, 3)
    if (ids.length < 2) {
      setLoading(false)
      return
    }

    async function load() {
      const supabase = createClient()
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/auth'); return }
      try {
        const results = await Promise.all(ids.map(id => getSimulation(id, session.access_token)))
        setSims(results.map(r => ({
          id: r.id,
          created_at: r.created_at,
          name: r.name,
          result: r.result.result,
          plan: r.result.result.plan,
        })))
      } catch (e) {
        setError(e instanceof ApiError ? e.message : t('compare.error'))
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [searchParams, router, t])

  if (loading) {
    return (
      <div className="flex justify-center p-12" role="status" aria-live="polite" aria-busy="true" aria-label={t('compare.loading')}>
        <svg aria-hidden="true" className="animate-spin h-8 w-8 text-gray-400 dark:text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <p className="text-red-500 text-sm">{error}</p>
      </div>
    )
  }

  if (!sims || sims.length < 2) {
    return (
      <div className="text-center py-16">
        <p className="mb-4 text-gray-500 dark:text-gray-400">{t('compare.no_data')}</p>
        <Link href="/history" className="inline-flex items-center justify-center rounded-lg bg-black text-white dark:bg-white dark:text-black px-6 py-3 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900">
          {t('nav.history')}
        </Link>
      </div>
    )
  }

  return <CompareTable sims={sims} />
}

export default function ComparePage() {
  const { t } = useI18n()
  return (
    <main className="min-h-screen p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('compare.title')}</h1>
        <div className="flex items-center gap-3">
          <DarkModeToggle />
          <LocaleToggle />
          <Link href="/history" className="text-sm border dark:border-gray-700 rounded-lg px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400 dark:focus-visible:ring-offset-gray-900">
            {t('nav.history')}
          </Link>
        </div>
      </div>

      <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
        <Suspense fallback={
          <div className="flex justify-center p-12" role="status" aria-live="polite" aria-busy="true" aria-label={t('compare.loading')}>
            <svg aria-hidden="true" className="animate-spin h-8 w-8 text-gray-400 dark:text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        }>
          <CompareInner />
        </Suspense>
      </div>

      <div className="mt-6 text-center">
        <Link href="/" className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">{t('nav.home')}</Link>
      </div>
    </main>
  )
}
