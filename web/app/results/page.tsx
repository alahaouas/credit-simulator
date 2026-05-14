'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { SimulateResponse } from '@/lib/api'
import dynamic from 'next/dynamic'
import AmortizationTable from '@/components/AmortizationTable'

const LoanChart = dynamic(() => import('@/components/LoanChart'), { ssr: false })

function fmt(val: string, currency = '') {
  return `${currency}${parseFloat(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-4 flex flex-col gap-1">
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
      <span className="text-lg font-semibold">{value}</span>
    </div>
  )
}

export default function ResultsPage() {
  const [data, setData] = useState<SimulateResponse | null>(null)

  useEffect(() => {
    const raw = sessionStorage.getItem('simulator_result')
    if (raw) setData(JSON.parse(raw))
  }, [])

  if (!data) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">No results yet.</p>
          <Link href="/simulate" className="rounded-lg bg-black text-white px-6 py-3 font-medium hover:bg-gray-800 transition-colors">
            Run a simulation
          </Link>
        </div>
      </main>
    )
  }

  const { result, sweet_spot, schedule } = data
  const { plan, currency } = result
  const c = currency || '€'

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Simulation results</h1>
        <Link href="/simulate" className="text-sm border rounded-lg px-4 py-2 hover:bg-gray-50 transition-colors">
          New simulation
        </Link>
      </div>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-3">Optimal loan plan</h2>
        <p className="text-sm text-gray-500 mb-4">
          {result.country} · {result.profile_quality} profile · {result.optimization_preference.replace(/_/g, ' ')}
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatCard label="Property price" value={fmt(result.property_price, c)} />
          <StatCard label="Down payment" value={fmt(result.down_payment, c)} />
          <StatCard label="Loan principal" value={fmt(result.loan_principal, c)} />
          <StatCard label="Duration" value={`${result.loan_duration_months} months`} />
          <StatCard label="Monthly installment" value={fmt(plan.monthly_installment, c)} />
          <StatCard label="Interest rate" value={`${parseFloat(plan.annual_interest_rate) * 100}%`} />
          <StatCard label="Total interest" value={fmt(plan.total_interest_paid, c)} />
          <StatCard label="Total insurance" value={fmt(plan.total_insurance_paid, c)} />
          <StatCard label="Total cost of credit" value={fmt(plan.total_cost_of_credit, c)} />
        </div>
      </section>

      {sweet_spot && sweet_spot.milestones.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-1">Down-payment sweet-spot</h2>
          <p className="text-sm text-gray-500 mb-3">{sweet_spot.sweet_spot_reason}</p>
          {sweet_spot.reserve_warning && (
            <p className="text-sm text-amber-600 mb-3">{sweet_spot.reserve_warning}</p>
          )}
          <div className="overflow-x-auto rounded-lg border text-sm">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {['Down payment', 'Label', 'Monthly', 'Total cost', 'Net saving', 'LTV', 'Rate'].map(h => (
                    <th key={h} className="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sweet_spot.milestones.map((m, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-medium">{fmt(m.down_payment, c)}</td>
                    <td className="px-3 py-2 text-gray-500">{m.label}</td>
                    <td className="px-3 py-2">{fmt(m.monthly_installment, c)}</td>
                    <td className="px-3 py-2">{fmt(m.total_cost_of_credit, c)}</td>
                    <td className="px-3 py-2 text-green-600">{fmt(m.net_saving_vs_previous, c)}</td>
                    <td className="px-3 py-2">{(parseFloat(m.ltv_ratio) * 100).toFixed(1)}%</td>
                    <td className="px-3 py-2">{(parseFloat(m.rate) * 100).toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {schedule && schedule.length > 0 && (
        <section>
          <LoanChart rows={schedule} />
          <AmortizationTable rows={schedule} />
        </section>
      )}
    </main>
  )
}
