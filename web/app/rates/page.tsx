'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { listProfiles, refreshRate, CountryProfile, ApiError } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import { DarkModeToggle } from '@/components/DarkModeToggle'
import { LocaleToggle } from '@/components/LocaleToggle'

type SortKey = keyof Pick<
  CountryProfile,
  'code' | 'currency' | 'annual_rate_average' | 'annual_rate_best' |
  'insurance_rate_average' | 'purchase_tax_rate' | 'min_down_payment_ratio' |
  'max_debt_ratio' | 'max_loan_duration_months'
>

function pct(v: string) {
  return `${(parseFloat(v) * 100).toFixed(2)}%`
}

export default function RatesPage() {
  const { t } = useI18n()
  const [profiles, setProfiles] = useState<Record<string, CountryProfile>>({})
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState<SortKey>('code')
  const [sortAsc, setSortAsc] = useState(true)
  const [refreshing, setRefreshing] = useState<Record<string, boolean>>({})
  const [refreshError, setRefreshError] = useState<Record<string, string>>({})

  useEffect(() => {
    listProfiles()
      .then(res => setProfiles(res.profiles))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSort = (key: SortKey) => {
    if (key === sortKey) setSortAsc(a => !a)
    else { setSortKey(key); setSortAsc(true) }
  }

  const handleRefresh = useCallback(async (code: string) => {
    setRefreshing(r => ({ ...r, [code]: true }))
    setRefreshError(e => ({ ...e, [code]: '' }))
    try {
      const res = await refreshRate(code)
      setProfiles(prev => ({
        ...prev,
        [code]: { ...prev[code], annual_rate_average: res.annual_rate_average },
      }))
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : t('rates.refresh_error')
      setRefreshError(e => ({ ...e, [code]: msg }))
    } finally {
      setRefreshing(r => ({ ...r, [code]: false }))
    }
  }, [t])

  const sorted = Object.values(profiles).sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    if (typeof av === 'number' && typeof bv === 'number') {
      return sortAsc ? av - bv : bv - av
    }
    return sortAsc
      ? String(av).localeCompare(String(bv))
      : String(bv).localeCompare(String(av))
  })

  const SortHeader = ({ col, label }: { col: SortKey; label: string }) => (
    <th
      className="text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap select-none"
      aria-sort={sortKey === col ? (sortAsc ? 'ascending' : 'descending') : 'none'}
    >
      <button
        type="button"
        onClick={() => handleSort(col)}
        className="flex items-center w-full text-left px-3 py-2 hover:text-gray-800 dark:hover:text-gray-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded transition-colors"
      >
        {label}
        <span className="ml-1 w-3 text-center">
          {sortKey === col ? (sortAsc ? '↑' : '↓') : ''}
        </span>
      </button>
    </th>
  )

  return (
    <main className="min-h-screen p-8">
      <div className="absolute top-4 right-4 flex items-center gap-3">
        <DarkModeToggle />
        <LocaleToggle />
      </div>

      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <Link href="/" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:focus-visible:ring-gray-600 rounded">
            {t('nav.home')}
          </Link>
        </div>

        <h1 className="text-2xl font-bold tracking-tight mb-1">{t('rates.title')}</h1>
        <p className="text-gray-500 dark:text-gray-400 mb-6">{t('rates.subtitle')}</p>

        {loading ? (
          <p className="text-gray-400">{t('rates.loading')}</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <SortHeader col="code" label={t('rates.col_country')} />
                  <SortHeader col="currency" label={t('rates.col_currency')} />
                  <SortHeader col="annual_rate_average" label={t('rates.col_avg_rate')} />
                  <SortHeader col="annual_rate_best" label={t('rates.col_best_rate')} />
                  <SortHeader col="insurance_rate_average" label={t('rates.col_ins_avg')} />
                  <SortHeader col="purchase_tax_rate" label={t('rates.col_purchase_tax')} />
                  <SortHeader col="min_down_payment_ratio" label={t('rates.col_min_down')} />
                  <SortHeader col="max_debt_ratio" label={t('rates.col_max_debt')} />
                  <SortHeader col="max_loan_duration_months" label={t('rates.col_max_duration')} />
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {t('rates.col_updated')}
                  </th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-900">
                {sorted.map(p => (
                  <tr key={p.code} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    <td className="px-3 py-2 font-semibold">{p.code}</td>
                    <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{p.currency}</td>
                    <td className="px-3 py-2 tabular-nums">{pct(p.annual_rate_average)}</td>
                    <td className="px-3 py-2 tabular-nums text-green-700 dark:text-green-400">{pct(p.annual_rate_best)}</td>
                    <td className="px-3 py-2 tabular-nums">{pct(p.insurance_rate_average)}</td>
                    <td className="px-3 py-2 tabular-nums">{pct(p.purchase_tax_rate)}</td>
                    <td className="px-3 py-2 tabular-nums">{pct(p.min_down_payment_ratio)}</td>
                    <td className="px-3 py-2 tabular-nums">{pct(p.max_debt_ratio)}</td>
                    <td className="px-3 py-2 tabular-nums">{p.max_loan_duration_months}</td>
                    <td className="px-3 py-2 text-gray-400 text-xs">{p.last_updated_date || t('rates.no_source')}</td>
                    <td className="px-3 py-2 text-right">
                      {refreshError[p.code] ? (
                        <span className="text-xs text-red-500">{t('rates.refresh_error')}</span>
                      ) : (
                        <button
                          onClick={() => handleRefresh(p.code)}
                          disabled={refreshing[p.code]}
                          aria-label={refreshing[p.code] ? t('aria.loading') : t('rates.refresh')}
                          className="flex items-center justify-center min-w-[80px] min-h-[24px] text-xs text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white disabled:opacity-40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded"
                        >
                          {refreshing[p.code] ? (
                            <svg aria-hidden="true" className="animate-spin h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                          ) : (
                            t('rates.refresh')
                          )}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </main>
  )
}
