'use client'

import { useState, useId } from 'react'
import { AmortizationRow } from '@/lib/api'
import { useI18n, type TranslationKey } from '@/lib/i18n'

function fmt(val: string) {
  return parseFloat(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const HEADER_KEYS: TranslationKey[] = [
  'amort.month',
  'amort.opening',
  'amort.interest',
  'amort.principal',
  'amort.insurance',
  'amort.total',
  'amort.closing',
]

export default function AmortizationTable({ rows }: { rows: AmortizationRow[] }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const contentId = useId()

  return (
    <div className="mt-6">
      <button
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-controls={contentId}
        className="text-sm font-medium underline underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded"
      >
        {open ? t('amort.hide') : t('amort.show')} ({rows.length} {t('stats.months')})
      </button>

      {open && (
        <div id={contentId} className="mt-3 overflow-x-auto rounded-lg border dark:border-gray-700 text-sm">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800">
              <tr>
                {HEADER_KEYS.map(k => (
                  <th key={k} className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">{t(k)}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {rows.map(r => (
                <tr key={r.period} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-3 py-1.5 text-gray-500 dark:text-gray-400">{r.period}</td>
                  <td className="px-3 py-1.5">{fmt(r.opening_balance)}</td>
                  <td className="px-3 py-1.5 text-red-600 dark:text-red-400">{fmt(r.interest_component)}</td>
                  <td className="px-3 py-1.5 text-green-600 dark:text-green-400">{fmt(r.principal_component)}</td>
                  <td className="px-3 py-1.5">{fmt(r.insurance_component)}</td>
                  <td className="px-3 py-1.5 font-medium">{fmt(r.monthly_installment)}</td>
                  <td className="px-3 py-1.5">{fmt(r.closing_balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
