'use client'

import { useState } from 'react'
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

  return (
    <div className="mt-6">
      <button
        onClick={() => setOpen(o => !o)}
        className="text-sm font-medium underline underline-offset-2"
      >
        {open ? t('amort.hide') : t('amort.show')} ({rows.length} {t('stats.months')})
      </button>

      {open && (
        <div className="mt-3 overflow-x-auto rounded-lg border text-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {HEADER_KEYS.map(k => (
                  <th key={k} className="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">{t(k)}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(r => (
                <tr key={r.period} className="hover:bg-gray-50">
                  <td className="px-3 py-1.5 text-gray-500">{r.period}</td>
                  <td className="px-3 py-1.5">{fmt(r.opening_balance)}</td>
                  <td className="px-3 py-1.5 text-red-600">{fmt(r.interest_component)}</td>
                  <td className="px-3 py-1.5 text-green-600">{fmt(r.principal_component)}</td>
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
