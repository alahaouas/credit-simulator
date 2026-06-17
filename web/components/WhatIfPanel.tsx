'use client'

import { useEffect, useRef, useState } from 'react'
import { simulate, SimulateRequest, SimulateResponse, ApiError } from '@/lib/api'
import { DEFAULT_CURRENCY_SYMBOL } from '@/lib/constants'
import { useI18n } from '@/lib/i18n'

const inputClass =
  'border dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-gray-400 w-full'

function fmtNum(val: string) {
  return parseFloat(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

interface Props {
  original: SimulateResponse
  originalRequest: SimulateRequest
  currency: string
}

export default function WhatIfPanel({ original, originalRequest, currency }: Props) {
  const { t } = useI18n()
  const { result } = original
  const c = currency || DEFAULT_CURRENCY_SYMBOL

  const origRate = (parseFloat(result.plan.annual_interest_rate) * 100).toFixed(2)
  const origDuration = result.loan_duration_months.toString()
  const origDownPayment = result.down_payment

  const [tweaks, setTweaks] = useState({
    rate: origRate,
    duration: origDuration,
    down_payment: origDownPayment,
  })
  const [tweaked, setTweaked] = useState<SimulateResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const isDirty =
    parseFloat(tweaks.rate) !== parseFloat(origRate) ||
    parseInt(tweaks.duration, 10) !== parseInt(origDuration, 10) ||
    parseFloat(tweaks.down_payment) !== parseFloat(origDownPayment)

  function reset() {
    setTweaks({ rate: origRate, duration: origDuration, down_payment: origDownPayment })
    setTweaked(null)
    setError(null)
  }

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)

    const rateNum = parseFloat(tweaks.rate)
    const durationNum = parseInt(tweaks.duration, 10)
    const dpNum = parseFloat(tweaks.down_payment)

    const dirty =
      rateNum !== parseFloat(origRate) ||
      durationNum !== parseInt(origDuration, 10) ||
      dpNum !== parseFloat(origDownPayment)

    if (!dirty) {
      setTweaked(null)
      return
    }

    timerRef.current = setTimeout(async () => {
      if (isNaN(rateNum) || isNaN(durationNum) || isNaN(dpNum)) return

      setLoading(true)
      setError(null)
      try {
        const req: SimulateRequest = {
          ...originalRequest,
          annual_interest_rate: (rateNum / 100).toFixed(6),
          fixed_loan_duration_months: durationNum,
          preferred_down_payment: dpNum.toString(),
          include_schedule: false,
          include_sweet_spot: false,
        }
        const res = await simulate(req)
        setTweaked(res)
      } catch (e) {
        setError(e instanceof ApiError ? e.message : t('whatif.error'))
      } finally {
        setLoading(false)
      }
    }, 600)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [tweaks])

  const ref = result.plan
  const twk = tweaked?.result.plan

  function deltaDisplay(tweakedVal: string, origVal: string) {
    const diff = parseFloat(tweakedVal) - parseFloat(origVal)
    const abs = Math.abs(diff).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    const sign = diff > 0 ? '+' : diff < 0 ? '-' : ''
    return { text: `${sign}${c}${abs}`, positive: diff < 0 }
  }

  const deltaMonths = tweaked
    ? tweaked.result.loan_duration_months - result.loan_duration_months
    : null

  const monetaryRows = twk
    ? [
        { label: t('whatif.monthly'), orig: ref.monthly_installment, tw: twk.monthly_installment },
        { label: t('whatif.total_interest'), orig: ref.total_interest_paid, tw: twk.total_interest_paid },
        { label: t('whatif.total_cost'), orig: ref.total_cost_of_credit, tw: twk.total_cost_of_credit },
      ]
    : []

  return (
    <section className="mb-8 border dark:border-gray-700 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">{t('whatif.title')}</h2>
        {isDirty && (
          <button
            onClick={reset}
            className="text-sm text-gray-500 hover:text-black dark:hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded"
          >
            {t('whatif.reset')}
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="whatif-rate" className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            {t('whatif.rate')} (%)
          </label>
          <input
            id="whatif-rate"
            type="number"
            min="0"
            max="20"
            step="0.01"
            value={tweaks.rate}
            onChange={e => setTweaks(s => ({ ...s, rate: e.target.value }))}
            className={inputClass}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="whatif-duration" className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            {t('whatif.duration')}
          </label>
          <input
            id="whatif-duration"
            type="number"
            min="12"
            max="360"
            step="12"
            value={tweaks.duration}
            onChange={e => setTweaks(s => ({ ...s, duration: e.target.value }))}
            className={inputClass}
          />
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="whatif-down-payment" className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            {t('whatif.down_payment')} ({c})
          </label>
          <input
            id="whatif-down-payment"
            type="number"
            min="0"
            step="1000"
            value={tweaks.down_payment}
            onChange={e => setTweaks(s => ({ ...s, down_payment: e.target.value }))}
            className={inputClass}
          />
        </div>
      </div>

      {loading && <p className="text-sm text-gray-500 dark:text-gray-400">{t('whatif.loading')}</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {twk && !loading && (
        <div className="overflow-x-auto rounded-lg border dark:border-gray-700 text-sm">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide" />
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  {t('whatif.original')}
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  {t('whatif.tweaked')}
                </th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  {t('whatif.delta')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {monetaryRows.map(({ label, orig, tw }) => {
                const d = deltaDisplay(tw, orig)
                return (
                  <tr key={label} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-3 py-2 text-gray-500 dark:text-gray-400 font-medium">{label}</td>
                    <td className="px-3 py-2">
                      {c}
                      {fmtNum(orig)}
                    </td>
                    <td className="px-3 py-2 font-medium">
                      {c}
                      {fmtNum(tw)}
                    </td>
                    <td
                      data-testid={`whatif-delta-${label}`}
                      className={`px-3 py-2 font-medium ${d.positive ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}`}
                    >
                      {d.text}
                    </td>
                  </tr>
                )
              })}
              {deltaMonths !== null && (
                <tr className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-3 py-2 text-gray-500 dark:text-gray-400 font-medium">{t('results.duration')}</td>
                  <td className="px-3 py-2">
                    {result.loan_duration_months} {t('stats.months')}
                  </td>
                  <td className="px-3 py-2 font-medium">
                    {tweaked!.result.loan_duration_months} {t('stats.months')}
                  </td>
                  <td
                    data-testid="whatif-delta-duration"
                    className={`px-3 py-2 font-medium ${deltaMonths < 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}`}
                  >
                    {deltaMonths > 0 ? '+' : ''}
                    {deltaMonths} {t('stats.months')}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
