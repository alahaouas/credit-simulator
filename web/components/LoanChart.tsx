'use client'

import { AmortizationRow } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import { useTheme } from './ThemeProvider'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

export default function LoanChart({ rows }: { rows: AmortizationRow[] }) {
  const { t } = useI18n()
  const { theme } = useTheme()
  const isDark = theme === 'dark'

  const data = rows.map(r => ({
    month: r.period,
    balance: parseFloat(r.closing_balance),
  }))

  const gridColor = isDark ? '#374151' : '#f0f0f0'
  const lineColor = isDark ? '#e5e7eb' : '#000000'
  const tickColor = isDark ? '#9ca3af' : '#6b7280'

  return (
    <div className="mt-6">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">{t('chart.balance_title')}</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12, fill: tickColor }}
            label={{ value: t('chart.month_axis'), position: 'insideBottom', offset: -2, fontSize: 12, fill: tickColor }}
          />
          <YAxis tick={{ fontSize: 12, fill: tickColor }} tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
          <Tooltip
            formatter={(v) => Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            contentStyle={isDark ? { backgroundColor: '#1f2937', border: '1px solid #374151', color: '#f3f4f6' } : undefined}
          />
          <Line type="monotone" dataKey="balance" stroke={lineColor} dot={false} strokeWidth={2} name={t('amort.closing')} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
