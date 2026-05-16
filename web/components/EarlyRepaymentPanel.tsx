'use client'

import { useState } from 'react'
import { OptimizedResult } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

interface Props {
  result: OptimizedResult
  currency: string
}

interface RepaymentSummary {
  balanceAtLumpSum: number
  newTotalMonths: number
  monthsSaved: number
  originalTotalInterest: number
  newTotalInterest: number
  interestSaved: number
  revisedSchedule: RevisedRow[]
}

interface RevisedRow {
  period: number
  balance: number
  interest: number
  principal: number
  installment: number
}

function computeRepayment(
  principal: number,
  annualRate: number,
  annualInsuranceRate: number,
  durationMonths: number,
  emi: number,
  lumpSumMonth: number,
  lumpSumAmount: number,
): RepaymentSummary | null {
  const monthlyRate = annualRate / 12
  const monthlyInsurance = (principal * annualInsuranceRate) / 12

  // Walk the schedule to find the balance just before lump-sum month
  let balance = principal
  let originalInterest = 0
  const preRows: RevisedRow[] = []

  for (let m = 1; m <= Math.min(lumpSumMonth, durationMonths); m++) {
    const interest = balance * monthlyRate
    const principalPaid = emi - interest
    if (principalPaid <= 0) return null // degenerate: EMI too small
    originalInterest += interest
    preRows.push({ period: m, balance, interest, principal: principalPaid, installment: emi + monthlyInsurance })
    balance -= principalPaid
  }

  if (balance <= 0) return null // already paid off before lump-sum month

  const balanceAtLumpSum = balance
  balance = Math.max(0, balance - lumpSumAmount)

  if (balance === 0) {
    // Paid off exactly at lump-sum month
    const originalRemaining = computeRemainingInterest(balanceAtLumpSum, monthlyRate, emi, durationMonths - lumpSumMonth)
    return {
      balanceAtLumpSum,
      newTotalMonths: lumpSumMonth,
      monthsSaved: durationMonths - lumpSumMonth,
      originalTotalInterest: originalInterest + originalRemaining,
      newTotalInterest: originalInterest,
      interestSaved: originalRemaining,
      revisedSchedule: preRows,
    }
  }

  // Continue with same EMI until paid off
  const postRows: RevisedRow[] = []
  let newInterest = 0
  let remaining = 0
  const MAX_MONTHS = durationMonths * 2

  while (balance > 0.005 && remaining < MAX_MONTHS) {
    const interest = balance * monthlyRate
    if (emi <= interest) return null // EMI too small to ever pay off
    const principalPaid = Math.min(emi - interest, balance)
    newInterest += interest
    remaining++
    postRows.push({
      period: lumpSumMonth + remaining,
      balance,
      interest,
      principal: principalPaid,
      installment: principalPaid + interest + monthlyInsurance,
    })
    balance -= principalPaid
  }

  const originalRemaining = computeRemainingInterest(balanceAtLumpSum, monthlyRate, emi, durationMonths - lumpSumMonth)

  return {
    balanceAtLumpSum,
    newTotalMonths: lumpSumMonth + remaining,
    monthsSaved: durationMonths - (lumpSumMonth + remaining),
    originalTotalInterest: originalInterest + originalRemaining,
    newTotalInterest: originalInterest + newInterest,
    interestSaved: originalRemaining - newInterest,
    revisedSchedule: [...preRows, ...postRows],
  }
}

function computeRemainingInterest(balance: number, monthlyRate: number, emi: number, months: number): number {
  let total = 0
  for (let m = 0; m < months && balance > 0.005; m++) {
    const interest = balance * monthlyRate
    if (emi <= interest) break
    total += interest
    balance -= emi - interest
  }
  return total
}

function fmt(val: number, currency: string) {
  return `${currency}${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const inputClass =
  'border dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-gray-400 w-full text-sm'

export default function EarlyRepaymentPanel({ result, currency }: Props) {
  const { t } = useI18n()
  const c = currency

  const principal = parseFloat(result.loan_principal)
  const annualRate = parseFloat(result.plan.annual_interest_rate)
  const annualInsuranceRate = parseFloat(result.plan.annual_insurance_rate)
  const durationMonths = result.loan_duration_months
  const emi = parseFloat(result.plan.monthly_emi)

  const [month, setMonth] = useState('')
  const [lumpSum, setLumpSum] = useState('')
  const [showSchedule, setShowSchedule] = useState(false)
  const [summary, setSummary] = useState<RepaymentSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  function handleCompute() {
    setError(null)
    setSummary(null)

    const m = parseInt(month, 10)
    const ls = parseFloat(lumpSum)

    if (!m || m < 1 || m >= durationMonths) {
      setError(`${t('early.error_month')} (1 – ${durationMonths - 1})`)
      return
    }
    if (!ls || ls <= 0) {
      setError(t('early.error_amount'))
      return
    }

    const result_ = computeRepayment(principal, annualRate, annualInsuranceRate, durationMonths, emi, m, ls)
    if (!result_) {
      setError(t('early.error_generic'))
      return
    }
    setSummary(result_)
  }

  return (
    <section className="mb-8 border dark:border-gray-700 rounded-xl p-5">
      <h2 className="text-lg font-semibold mb-1">{t('early.title')}</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{t('early.subtitle')}</p>

      <div className="flex flex-wrap gap-3 mb-4">
        <div className="flex-1 min-w-[140px]">
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">{t('early.month_label')}</label>
          <input
            type="number"
            min={1}
            max={durationMonths - 1}
            value={month}
            onChange={e => setMonth(e.target.value)}
            placeholder={`1 – ${durationMonths - 1}`}
            className={inputClass}
          />
        </div>
        <div className="flex-1 min-w-[180px]">
          <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">{t('early.amount_label')} ({c})</label>
          <input
            type="number"
            min={1}
            value={lumpSum}
            onChange={e => setLumpSum(e.target.value)}
            placeholder="10 000"
            className={inputClass}
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={handleCompute}
            className="px-5 py-2 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors"
          >
            {t('early.compute')}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400 mb-3">{error}</p>}

      {summary && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
            <Stat label={t('early.balance_at_lump')} value={fmt(summary.balanceAtLumpSum, c)} />
            <Stat label={t('early.new_duration')} value={`${summary.newTotalMonths} ${t('stats.months')}`} />
            <Stat label={t('early.months_saved')} value={`${summary.monthsSaved} ${t('stats.months')}`} highlight={summary.monthsSaved > 0} />
            <Stat label={t('early.orig_interest')} value={fmt(summary.originalTotalInterest, c)} />
            <Stat label={t('early.new_interest')} value={fmt(summary.newTotalInterest, c)} />
            <Stat label={t('early.interest_saved')} value={fmt(summary.interestSaved, c)} highlight={summary.interestSaved > 0} />
          </div>

          <button
            onClick={() => setShowSchedule(s => !s)}
            className="text-sm text-gray-500 dark:text-gray-400 underline mb-3"
          >
            {showSchedule ? t('early.hide_schedule') : t('early.show_schedule')}
          </button>

          {showSchedule && (
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700 text-xs max-h-80 overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                  <tr>
                    {(['early.col_period', 'early.col_balance', 'early.col_interest', 'early.col_principal', 'early.col_installment'] as const).map(k => (
                      <th key={k} className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">{t(k)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {summary.revisedSchedule.map((row, i) => {
                    const isLumpSumRow = row.period === parseInt(month, 10)
                    return (
                      <tr key={i} className={isLumpSumRow ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800'}>
                        <td className="px-3 py-1.5 font-medium">{row.period}{isLumpSumRow ? ' ★' : ''}</td>
                        <td className="px-3 py-1.5">{fmt(row.balance, c)}</td>
                        <td className="px-3 py-1.5">{fmt(row.interest, c)}</td>
                        <td className="px-3 py-1.5">{fmt(row.principal, c)}</td>
                        <td className="px-3 py-1.5">{fmt(row.installment, c)}</td>
                      </tr>
                    )
                  })}
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
