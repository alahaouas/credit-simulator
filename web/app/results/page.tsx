'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { SimulateRequest, SimulateResponse, SimulateAllResponse, simulateAll, ApiError, OptimizedResult } from '@/lib/api'
import { DEFAULT_CURRENCY_SYMBOL, SESSION_INPUTS_KEY, SESSION_RESULT_KEY, SESSION_ALL_PREFS_KEY } from '@/lib/constants'
import { OPTIMIZATION_PREFERENCES } from '@/lib/constants'
import { useI18n, type TranslationKey } from '@/lib/i18n'
import dynamic from 'next/dynamic'
import AmortizationTable from '@/components/AmortizationTable'
import { DarkModeToggle } from '@/components/DarkModeToggle'
import WhatIfPanel from '@/components/WhatIfPanel'
import EarlyRepaymentPanel from '@/components/EarlyRepaymentPanel'
import RefinancingBreakEvenPanel from '@/components/RefinancingBreakEvenPanel'
import OpportunityCostPanel from '@/components/OpportunityCostPanel'
import SweetSpotHeatmap from '@/components/SweetSpotHeatmap'
import PurchaseTaxPanel from '@/components/PurchaseTaxPanel'

const LoanChart = dynamic(() => import('@/components/LoanChart'), { ssr: false })

const PREFERENCE_LABEL_KEY: Record<string, TranslationKey> = {
  balanced: 'pref.balanced',
  minimize_total_cost: 'pref.minimize_total_cost',
  minimize_monthly_payment: 'pref.minimize_monthly_payment',
  minimize_duration: 'pref.minimize_duration',
  minimize_down_payment: 'pref.minimize_down_payment',
}

function fmt(val: string, currency = '') {
  return `${currency}${parseFloat(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function csvField(value: string | number): string {
  const s = String(value)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

function exportScheduleToCsv(rows: SimulateResponse['schedule'], currency: string) {
  if (!rows) return
  const headers = ['Period', 'Opening Balance', 'Monthly Installment', 'Principal', 'Interest', 'Insurance', 'Closing Balance']
  const lines = [
    headers.join(','),
    ...rows.map(r =>
      [r.period, r.opening_balance, r.monthly_installment, r.principal_component, r.interest_component, r.insurance_component, r.closing_balance]
        .map(csvField)
        .join(',')
    ),
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `amortization_${currency}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border dark:border-gray-700 p-4 flex flex-col gap-1">
      <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</span>
      <span className="text-lg font-semibold">{value}</span>
    </div>
  )
}

export default function ResultsPage() {
  const { t } = useI18n()
  const [data, setData] = useState<SimulateResponse | null>(null)
  const [inputs, setInputs] = useState<SimulateRequest | null>(null)
  const [allPrefs, setAllPrefs] = useState<SimulateAllResponse | null>(null)
  const [allPrefsLoading, setAllPrefsLoading] = useState(false)
  const [allPrefsError, setAllPrefsError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<string>('balanced')

  useEffect(() => {
    const raw = sessionStorage.getItem(SESSION_RESULT_KEY)
    if (raw) {
      try { setData(JSON.parse(raw)) } catch { /* ignore malformed */ }
    }
    const rawInputs = sessionStorage.getItem(SESSION_INPUTS_KEY)
    if (rawInputs) {
      try { setInputs(JSON.parse(rawInputs)) } catch { /* ignore malformed */ }
    }
    const rawAll = sessionStorage.getItem(SESSION_ALL_PREFS_KEY)
    if (rawAll) {
      try { setAllPrefs(JSON.parse(rawAll)) } catch { /* ignore malformed */ }
    }
  }, [])

  async function handleCompareAll() {
    if (!inputs) return
    setAllPrefsLoading(true)
    setAllPrefsError(null)
    try {
      const resp = await simulateAll(inputs)
      setAllPrefs(resp)
      sessionStorage.setItem(SESSION_ALL_PREFS_KEY, JSON.stringify(resp))
    } catch (err) {
      setAllPrefsError(err instanceof ApiError ? err.message : String(err))
    } finally {
      setAllPrefsLoading(false)
    }
  }

  if (!data) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 dark:text-gray-400 mb-4">{t('results.no_results')}</p>
          <Link href="/simulate" className="rounded-lg bg-black text-white dark:bg-white dark:text-black px-6 py-3 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900">
            {t('nav.run')}
          </Link>
        </div>
      </main>
    )
  }

  const { result, sweet_spot, schedule } = data
  const { plan, currency } = result
  const c = currency || DEFAULT_CURRENCY_SYMBOL
  const prefKey = PREFERENCE_LABEL_KEY[result.optimization_preference]
  const prefLabel = prefKey ? t(prefKey) : result.optimization_preference.replace(/_/g, ' ')

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('results.title')}</h1>
        <div className="flex items-center gap-3">
          <DarkModeToggle />
          {inputs && (
            <button
              onClick={handleCompareAll}
              disabled={allPrefsLoading}
              aria-label={allPrefsLoading ? t('aria.loading') : t('results.compare_all')}
              className="inline-flex items-center justify-center min-w-[130px] min-h-[38px] text-sm border dark:border-gray-700 rounded-lg px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400 dark:focus-visible:ring-offset-gray-900"
            >
              {allPrefsLoading ? (
                <svg aria-hidden="true" className="animate-spin h-4 w-4 text-gray-500 dark:text-gray-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                t('results.compare_all')
              )}
            </button>
          )}
          <Link href="/simulate" className="inline-flex items-center justify-center min-h-[38px] text-sm border dark:border-gray-700 rounded-lg px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400 dark:focus-visible:ring-offset-gray-900">
            {t('results.new')}
          </Link>
        </div>
      </div>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-3">{t('results.optimal_plan')}</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          {result.country} · {result.profile_quality} {t('results.profile_suffix')} · {prefLabel}
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatCard label={t('results.property_price')} value={fmt(result.property_price, c)} />
          <StatCard label={t('results.down_payment')} value={fmt(result.down_payment, c)} />
          <StatCard label={t('results.loan_principal')} value={fmt(result.loan_principal, c)} />
          <StatCard label={t('results.duration')} value={`${result.loan_duration_months} ${t('stats.months')}`} />
          <StatCard label={t('results.monthly_installment')} value={fmt(plan.monthly_installment, c)} />
          <StatCard label={t('results.interest_rate')} value={`${(parseFloat(plan.annual_interest_rate) * 100).toFixed(2)}%`} />
          <StatCard label={t('results.total_interest')} value={fmt(plan.total_interest_paid, c)} />
          <StatCard label={t('results.total_insurance')} value={fmt(plan.total_insurance_paid, c)} />
          <StatCard label={t('results.total_cost')} value={fmt(plan.total_cost_of_credit, c)} />
        </div>
      </section>

      {inputs && (
        <WhatIfPanel original={data} originalRequest={inputs} currency={c} />
      )}

      <EarlyRepaymentPanel result={result} currency={c} />
      <RefinancingBreakEvenPanel result={result} currency={c} />
      <OpportunityCostPanel result={result} currency={c} />
      <PurchaseTaxPanel result={result} currency={c} />

      {inputs && (
        <SweetSpotHeatmap result={result} inputs={inputs} currency={c} />
      )}

      {allPrefsError && (
        <p className="text-sm text-red-600 dark:text-red-400 mb-4">{allPrefsError}</p>
      )}

      {allPrefs && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-3">{t('results.all_prefs_title')}</h2>
          <div className="flex gap-1 mb-4 flex-wrap">
            {OPTIMIZATION_PREFERENCES.map(pref => {
              const prefKey = PREFERENCE_LABEL_KEY[pref]
              const label = prefKey ? t(prefKey) : pref.replace(/_/g, ' ')
              const isNull = allPrefs.results[pref] === null
              return (
                <button
                  key={pref}
                  onClick={() => setActiveTab(pref)}
                  className={`px-3 py-1.5 text-sm rounded-lg border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400 dark:focus-visible:ring-offset-gray-900 ${
                    activeTab === pref
                      ? 'bg-black text-white dark:bg-white dark:text-black border-black dark:border-white'
                      : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800'
                  } ${isNull ? 'opacity-40 cursor-not-allowed' : ''}`}
                  disabled={isNull}
                >
                  {label}
                </button>
              )
            })}
          </div>
          {(() => {
            const r = allPrefs.results[activeTab] as OptimizedResult | null
            if (!r) {
              return <p className="text-sm text-gray-500 dark:text-gray-400">{t('results.all_prefs_error')}</p>
            }
            const rc = r.currency || c
            return (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <StatCard label={t('results.down_payment')} value={fmt(r.down_payment, rc)} />
                <StatCard label={t('results.loan_principal')} value={fmt(r.loan_principal, rc)} />
                <StatCard label={t('results.duration')} value={`${r.loan_duration_months} ${t('stats.months')}`} />
                <StatCard label={t('results.monthly_installment')} value={fmt(r.plan.monthly_installment, rc)} />
                <StatCard label={t('results.interest_rate')} value={`${(parseFloat(r.plan.annual_interest_rate) * 100).toFixed(2)}%`} />
                <StatCard label={t('results.total_cost')} value={fmt(r.plan.total_cost_of_credit, rc)} />
              </div>
            )
          })()}
        </section>
      )}

      {sweet_spot && sweet_spot.milestones.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-1">{t('results.sweet_spot_title')}</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">{sweet_spot.sweet_spot_reason}</p>
          {sweet_spot.reserve_warning && (
            <p className="text-sm text-amber-600 dark:text-amber-400 mb-3">{sweet_spot.reserve_warning}</p>
          )}
          <div className="overflow-x-auto rounded-lg border dark:border-gray-700 text-sm">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  {(
                    [
                      'sweet.down_payment',
                      'sweet.label',
                      'sweet.monthly',
                      'sweet.total_cost',
                      'sweet.net_saving',
                      'sweet.ltv',
                      'sweet.rate',
                    ] as TranslationKey[]
                  ).map(k => (
                    <th key={k} className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">{t(k)}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {sweet_spot.milestones.map((m, i) => (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-3 py-2 font-medium">{fmt(m.down_payment, c)}</td>
                    <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{m.label}</td>
                    <td className="px-3 py-2">{fmt(m.monthly_installment, c)}</td>
                    <td className="px-3 py-2">{fmt(m.total_cost_of_credit, c)}</td>
                    <td className="px-3 py-2 text-green-600 dark:text-green-400">{fmt(m.net_saving_vs_previous, c)}</td>
                    <td className="px-3 py-2">{(parseFloat(m.ltv_ratio) * 100).toFixed(1)}%</td>
                    <td className="px-3 py-2">{(parseFloat(m.rate) * 100).toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {schedule && schedule.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-2">
            <span />
            <button
              onClick={() => exportScheduleToCsv(schedule, c)}
              className="text-sm border dark:border-gray-700 rounded-lg px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400 dark:focus-visible:ring-offset-gray-900"
            >
              {t('results.export_csv')}
            </button>
          </div>
          <LoanChart rows={schedule} />
          <AmortizationTable rows={schedule} />
        </section>
      )}
    </main>
  )
}
