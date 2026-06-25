'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { getSharedSimulation, ApiError, SimulateResponse } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import { DarkModeToggle } from '@/components/DarkModeToggle'
import { LocaleToggle } from '@/components/LocaleToggle'

const PREFERENCE_LABEL: Record<string, string> = {
  balanced: 'Balanced',
  minimize_total_cost: 'Minimize total cost',
  minimize_monthly_payment: 'Minimize monthly payment',
  minimize_duration: 'Minimize duration',
  minimize_down_payment: 'Minimize down payment',
}

function fmt(val: string, currency = '') {
  return `${currency}${parseFloat(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'long' })
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-3 border-b dark:border-gray-700 last:border-0">
      <span className="text-sm text-gray-500 dark:text-gray-400">{label}</span>
      <span className="text-sm font-semibold tabular-nums">{value}</span>
    </div>
  )
}

export default function SharePage() {
  const params = useParams()
  const token = Array.isArray(params.token) ? params.token[0] : params.token
  const { t } = useI18n()

  const [data, setData] = useState<{
    id: string
    created_at: string
    name?: string | null
    result: SimulateResponse
  } | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!token) { setLoading(false); setNotFound(true); return }
    getSharedSimulation(token)
      .then(setData)
      .catch(e => {
        if (e instanceof ApiError && e.status === 404) setNotFound(true)
      })
      .finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">{t('share.loading')}</p>
      </main>
    )
  }

  if (notFound || !data) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
        <p className="text-gray-500 dark:text-gray-400 text-center">{t('share.not_found')}</p>
        <Link href="/simulate" className="rounded-lg bg-black text-white dark:bg-white dark:text-black px-6 py-3 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900">
          {t('share.cta')}
        </Link>
      </main>
    )
  }

  const result = data.result.result
  const plan = result.plan
  const currency = result.currency ?? '€'

  return (
    <main className="min-h-screen p-8 max-w-lg mx-auto">
      <div className="absolute top-4 right-4 flex items-center gap-3">
        <DarkModeToggle />
        <LocaleToggle />
      </div>

      <div className="mb-6">
        <span className="inline-block text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 rounded-full px-3 py-1 mb-3">
          {t('share.badge')}
        </span>
        <h1 className="text-2xl font-bold tracking-tight">
          {data.name ?? t('share.title')}
        </h1>
        <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">{formatDate(data.created_at)}</p>
      </div>

      <div className="rounded-lg border dark:border-gray-700 p-5 mb-6">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
          {result.country} · {PREFERENCE_LABEL[result.optimization_preference] ?? result.optimization_preference}
        </h2>
        <MetricRow label={t('results.property_price')} value={fmt(result.property_price, currency)} />
        <MetricRow label={t('results.down_payment')} value={fmt(result.down_payment, currency)} />
        <MetricRow label={t('results.loan_principal')} value={fmt(result.loan_principal, currency)} />
        <MetricRow label={t('results.duration')} value={`${result.loan_duration_months} mo`} />
        <MetricRow label={t('results.monthly_installment')} value={fmt(plan.monthly_installment, currency)} />
        <MetricRow label={t('results.interest_rate')} value={`${parseFloat(plan.annual_interest_rate).toFixed(3)} %`} />
        <MetricRow label={t('results.total_interest')} value={fmt(plan.total_interest_paid, currency)} />
        <MetricRow label={t('results.total_cost')} value={fmt(plan.total_cost_of_credit, currency)} />
      </div>

      <div className="text-center">
        <Link href="/simulate" className="rounded-lg bg-black text-white dark:bg-white dark:text-black px-6 py-3 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900">
          {t('share.cta')}
        </Link>
      </div>
    </main>
  )
}
