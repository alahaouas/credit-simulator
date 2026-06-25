'use client'

import { useState } from 'react'
import { OptimizedResult } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

interface Props {
  result: OptimizedResult
  currency: string
}

interface BreakEvenSummary {
  newEmi: number
  monthlySavings: number
  breakEvenMonth: number | null
  remainingMonths: number
  origRemainingInterest: number
  newTotalInterest: number
  interestSaved: number
  tableRows: BreakEvenRow[]
}

interface BreakEvenRow {
  month: number
  cumulativeSavings: number
  netGain: number
  isBreakEven: boolean
}

function computeBreakEven(
  principal: number,
  originalAnnualRate: number,
  newAnnualRate: number,
  durationMonths: number,
  originalEmi: number,
  closingCosts: number,
): BreakEvenSummary | null {
  const newMonthlyRate = newAnnualRate / 12

  const newEmi =
    newMonthlyRate === 0
      ? principal / durationMonths
      : (principal * newMonthlyRate) / (1 - Math.pow(1 + newMonthlyRate, -durationMonths))

  const monthlySavings = originalEmi - newEmi
  if (monthlySavings <= 0) return null

  const origMonthlyRate = originalAnnualRate / 12
  let origRemainingInterest = 0
  let bal = principal
  for (let m = 0; m < durationMonths && bal > 0.005; m++) {
    const interest = bal * origMonthlyRate
    if (originalEmi <= interest) break
    origRemainingInterest += interest
    bal -= originalEmi - interest
  }

  let newTotalInterest = 0
  bal = principal
  for (let m = 0; m < durationMonths && bal > 0.005; m++) {
    const interest = bal * newMonthlyRate
    if (newEmi <= interest) break
    newTotalInterest += interest
    bal -= newEmi - interest
  }

  let breakEvenMonth: number | null = null
  const tableRows: BreakEvenRow[] = []
  for (let m = 1; m <= durationMonths; m++) {
    const cumulativeSavings = monthlySavings * m
    const netGain = cumulativeSavings - closingCosts
    const isBreakEven = netGain >= 0 && breakEvenMonth === null
    if (isBreakEven) breakEvenMonth = m
    tableRows.push({ month: m, cumulativeSavings, netGain, isBreakEven: netGain >= 0 && m === breakEvenMonth })
  }

  return {
    newEmi,
    monthlySavings,
    breakEvenMonth,
    remainingMonths: durationMonths,
    origRemainingInterest,
    newTotalInterest,
    interestSaved: origRemainingInterest - newTotalInterest,
    tableRows,
  }
}

function fmt(val: number, currency: string) {
  return `${currency}${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const inputClass =
  'border dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-gray-400 w-full text-sm'

export default function RefinancingBreakEvenPanel({ result, currency }: Props) {
  const { t } = useI18n()
  const c = currency

  const principal = parseFloat(result.loan_principal)
  const originalAnnualRate = parseFloat(result.plan.annual_interest_rate)
  const durationMonths = result.loan_duration_months
  const originalEmi = parseFloat(result.plan.monthly_emi)

  const [newRate, setNewRate] = useState('')
  const [closingCosts, setClosingCosts] = useState('')
  const [showTable, setShowTable] = useState(false)
  const [summary, setSummary] = useState<BreakEvenSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handleCompute() {
    setError(null)
    setSummary(null)

    const rate = parseFloat(newRate) / 100
    const costs = parseFloat(closingCosts)

    if (isNaN(rate) || rate <= 0 || rate >= originalAnnualRate) {
      setError(t('refi.error_rate'))
      return
    }
    if (isNaN(costs) || costs < 0) {
      setError(t('refi.error_costs'))
      return
    }

    const result_ = computeBreakEven(principal, originalAnnualRate, rate, durationMonths, originalEmi, costs)
    if (!result_) {
      setError(t('refi.no_savings'))
      return
    }
    setSummary(result_)
  }

  return (
    <section className="mb-8 border dark:border-gray-700 rounded-xl p-5">
      <h2 className="text-lg font-semibold mb-1">{t('refi.title')}</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{t('refi.subtitle')}</p>

      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex-1 min-w-[160px]">
          <label htmlFor="refi-rate" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
            {t('refi.new_rate_label')}
          </label>
          <input
            id="refi-rate"
            type="number"
            min={0.01}
            step={0.01}
            max={(originalAnnualRate * 100 - 0.01).toFixed(2)}
            value={newRate}
            onChange={e => setNewRate(e.target.value)}
            placeholder={`< ${(originalAnnualRate * 100).toFixed(2)}`}
            className={inputClass}
          />
        </div>
        <div className="flex-1 min-w-[180px]">
          <label htmlFor="refi-costs" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
            {t('refi.closing_costs_label')} ({c})
          </label>
          <input
            id="refi-costs"
            type="number"
            min={0}
            value={closingCosts}
            onChange={e => setClosingCosts(e.target.value)}
            placeholder="0"
            className={inputClass}
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={handleCompute}
            className="px-5 py-2 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900"
          >
            {t('refi.compute')}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400 mb-3">{error}</p>}

      {summary && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
            <Stat label={t('refi.new_emi')} value={fmt(summary.newEmi, c)} />
            <Stat label={t('refi.monthly_savings')} value={fmt(summary.monthlySavings, c)} highlight />
            <Stat
              label={t('refi.breakeven_month')}
              value={summary.breakEvenMonth != null ? `${summary.breakEvenMonth} ${t('stats.months')}` : t('refi.never')}
              highlight={summary.breakEvenMonth != null}
            />
            <Stat label={t('refi.orig_total_interest')} value={fmt(summary.origRemainingInterest, c)} />
            <Stat label={t('refi.new_total_interest')} value={fmt(summary.newTotalInterest, c)} />
            <Stat
              label={t('refi.interest_saved')}
              value={fmt(summary.interestSaved, c)}
              highlight={summary.interestSaved > 0}
            />
          </div>

          <button
            onClick={() => setShowTable(s => !s)}
            className="text-sm text-gray-500 dark:text-gray-400 underline mb-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded"
          >
            {showTable ? t('refi.hide_table') : t('refi.show_table')}
          </button>

          {showTable && (
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700 text-xs max-h-80 overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                  <tr>
                    {(['refi.col_month', 'refi.col_cumulative_savings', 'refi.col_net_gain', 'refi.col_breakeven'] as const).map(k => (
                      <th key={k} className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">
                        {t(k)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {summary.tableRows.map((row, i) => (
                    <tr
                      key={i}
                      className={
                        row.isBreakEven
                          ? 'bg-green-50 dark:bg-green-900/20 font-semibold'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                      }
                    >
                      <td className="px-3 py-1.5 font-medium">{row.month}{row.isBreakEven ? ' ★' : ''}</td>
                      <td className="px-3 py-1.5">{fmt(row.cumulativeSavings, c)}</td>
                      <td className={`px-3 py-1.5 ${row.netGain >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400'}`}>
                        {fmt(row.netGain, c)}
                      </td>
                      <td className="px-3 py-1.5">{row.isBreakEven ? '✓' : ''}</td>
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
