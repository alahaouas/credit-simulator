'use client'

import { useState } from 'react'
import { AmortizationRow } from '@/lib/api'

function fmt(val: string) {
  return parseFloat(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function AmortizationTable({ rows }: { rows: AmortizationRow[] }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="mt-6">
      <button
        onClick={() => setOpen(o => !o)}
        className="text-sm font-medium underline underline-offset-2"
      >
        {open ? 'Hide' : 'Show'} amortization schedule ({rows.length} months)
      </button>

      {open && (
        <div className="mt-3 overflow-x-auto rounded-lg border text-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {['Month', 'Opening', 'EMI', 'Interest', 'Principal', 'Insurance', 'Total', 'Closing'].map(h => (
                  <th key={h} className="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map(r => (
                <tr key={r.month} className="hover:bg-gray-50">
                  <td className="px-3 py-1.5 text-gray-500">{r.month}</td>
                  <td className="px-3 py-1.5">{fmt(r.opening_balance)}</td>
                  <td className="px-3 py-1.5">{fmt(r.emi)}</td>
                  <td className="px-3 py-1.5 text-red-600">{fmt(r.interest)}</td>
                  <td className="px-3 py-1.5 text-green-600">{fmt(r.principal)}</td>
                  <td className="px-3 py-1.5">{fmt(r.insurance)}</td>
                  <td className="px-3 py-1.5 font-medium">{fmt(r.total_payment)}</td>
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
