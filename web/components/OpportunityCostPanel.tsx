'use client'

import { useState } from 'react'
import { OptimizedResult } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

interface Props {
  result: OptimizedResult
  currency: string
}

interface ProjectionRow {
  label: string
  value: number
  growth: number
}

interface Projection {
  futureValue: number
  investmentGain: number
  rows: ProjectionRow[]
}

function computeProjection(
  downPayment: number,
  annualRate: number,
  durationMonths: number,
): Projection {
  const durationYears = durationMonths / 12
  const futureValue = downPayment * Math.pow(1 + annualRate, durationYears)

  const rows: ProjectionRow[] = []
  const fullYears = Math.floor(durationYears)
  for (let y = 1; y <= fullYears; y++) {
    const value = downPayment * Math.pow(1 + annualRate, y)
    rows.push({ label: `${y}`, value, growth: value - downPayment })
  }
  if (durationMonths % 12 !== 0) {
    rows.push({
      label: `${durationMonths} mo`,
      value: futureValue,
      growth: futureValue - downPayment,
    })
  }

  return {
    futureValue,
    investmentGain: futureValue - downPayment,
    rows,
  }
}

function fmt(val: number, currency: string) {
  return `${currency}${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const inputClass =
  'border dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-gray-400 w-full text-sm'

export default function OpportunityCostPanel({ result, currency }: Props) {
  const { t } = useI18n()
  const c = currency

  const downPayment = parseFloat(result.down_payment)
  const durationMonths = result.loan_duration_months
  const loanInterest = parseFloat(result.plan.total_interest_paid)

  const [rate, setRate] = useState('')
  const [showTable, setShowTable] = useState(false)
  const [projection, setProjection] = useState<Projection | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handleCompute() {
    setError(null)
    setProjection(null)

    const annualRate = parseFloat(rate) / 100
    if (isNaN(annualRate) || annualRate <= 0) {
      setError(t('opp.error_rate'))
      return
    }

    setProjection(computeProjection(downPayment, annualRate, durationMonths))
  }

  const years = (durationMonths / 12).toFixed(1)

  return (
    <section className="mb-8 border dark:border-gray-700 rounded-xl p-5">
      <h2 className="text-lg font-semibold mb-1">{t('opp.title')}</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{t('opp.subtitle')}</p>

      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex-1 min-w-[180px]">
          <label htmlFor="opp-rate" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
            {t('opp.rate_label')}
          </label>
          <input
            id="opp-rate"
            type="number"
            min={0.1}
            step={0.1}
            value={rate}
            onChange={e => setRate(e.target.value)}
            placeholder="5.0"
            className={inputClass}
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={handleCompute}
            className="px-5 py-2 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900"
          >
            {t('opp.compute')}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400 mb-3">{error}</p>}

      {projection && (
        <>
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
            {t('opp.summary_prefix')} {fmt(downPayment, c)} {t('opp.summary_at')} {rate}% {t('opp.summary_for')}{' '}
            {years} {t('opp.years')} → <strong>{fmt(projection.futureValue, c)}</strong>.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <Stat label={t('opp.invested')} value={fmt(downPayment, c)} />
            <Stat label={t('opp.future_value')} value={fmt(projection.futureValue, c)} />
            <Stat label={t('opp.investment_gain')} value={fmt(projection.investmentGain, c)} highlight />
            <Stat label={t('opp.loan_interest')} value={fmt(loanInterest, c)} />
          </div>

          <button
            onClick={() => setShowTable(s => !s)}
            aria-expanded={showTable}
            aria-controls="opportunity-cost-table"
            className="text-sm text-gray-500 dark:text-gray-400 underline mb-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded"
          >
            {showTable ? t('opp.hide_table') : t('opp.show_table')}
          </button>

          {showTable && (
            <div id="opportunity-cost-table" className="overflow-x-auto rounded-lg border dark:border-gray-700 text-xs max-h-80 overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                  <tr>
                    {(['opp.col_year', 'opp.col_value', 'opp.col_growth'] as const).map(k => (
                      <th key={k} className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        {t(k)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {projection.rows.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-3 py-1.5 font-medium">{row.label}</td>
                      <td className="px-3 py-1.5">{fmt(row.value, c)}</td>
                      <td className="px-3 py-1.5 text-green-600 dark:text-green-400">{fmt(row.growth, c)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function Stat({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-lg border dark:border-gray-700 p-3 flex flex-col gap-1">
      <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</span>
      <span className={`text-base font-semibold ${highlight ? 'text-green-600 dark:text-green-400' : ''}`}>{value}</span>
    </div>
  )
}
