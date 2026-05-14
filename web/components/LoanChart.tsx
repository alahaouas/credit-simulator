'use client'

import { AmortizationRow } from '@/lib/api'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

export default function LoanChart({ rows }: { rows: AmortizationRow[] }) {
  const data = rows.map(r => ({
    month: r.month,
    balance: parseFloat(r.closing_balance),
  }))

  return (
    <div className="mt-6">
      <h3 className="text-sm font-medium text-gray-700 mb-3">Outstanding balance over time</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="month" tick={{ fontSize: 12 }} label={{ value: 'Month', position: 'insideBottom', offset: -2, fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
          <Tooltip formatter={(v: number) => v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} />
          <Line type="monotone" dataKey="balance" stroke="#000" dot={false} strokeWidth={2} name="Balance" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
