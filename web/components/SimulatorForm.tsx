'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { simulate, SimulateRequest, ApiError } from '@/lib/api'

const COUNTRIES = ['BE', 'FR', 'DE', 'ES', 'IT', 'PT', 'GB', 'US']
const PREFERENCES = [
  { value: 'balanced', label: 'Balanced' },
  { value: 'minimize_total_cost', label: 'Minimize total cost' },
  { value: 'minimize_monthly_payment', label: 'Minimize monthly payment' },
  { value: 'minimize_duration', label: 'Minimize duration' },
  { value: 'minimize_down_payment', label: 'Minimize down payment' },
]

export default function SimulatorForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    property_price: '',
    monthly_net_income: '',
    available_savings: '',
    country: '',
    profile_quality: '',
    optimization_preference: 'balanced',
    include_schedule: false,
  })

  function set(field: string, value: string | boolean) {
    setForm(f => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const req: SimulateRequest = {
        property_price: form.property_price,
        monthly_net_income: form.monthly_net_income,
        available_savings: form.available_savings,
        optimization_preference: form.optimization_preference,
        include_sweet_spot: true,
        include_schedule: form.include_schedule,
        ...(form.country && { country: form.country }),
        ...(form.profile_quality && { profile_quality: form.profile_quality as 'average' | 'best' }),
      }
      const result = await simulate(req)
      sessionStorage.setItem('simulator_result', JSON.stringify(result))
      router.push('/results')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unexpected error — is the API running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5 w-full max-w-lg">
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium">Property price</label>
        <input
          type="number" min="0" step="any" required
          placeholder="300000"
          value={form.property_price}
          onChange={e => set('property_price', e.target.value)}
          className="border rounded px-3 py-2"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium">Monthly net income</label>
        <input
          type="number" min="0" step="any" required
          placeholder="3500"
          value={form.monthly_net_income}
          onChange={e => set('monthly_net_income', e.target.value)}
          className="border rounded px-3 py-2"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium">Available savings</label>
        <input
          type="number" min="0" step="any" required
          placeholder="60000"
          value={form.available_savings}
          onChange={e => set('available_savings', e.target.value)}
          className="border rounded px-3 py-2"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium">Country</label>
          <select
            value={form.country}
            onChange={e => set('country', e.target.value)}
            className="border rounded px-3 py-2 bg-white"
          >
            <option value="">Auto-detect</option>
            {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium">Profile quality</label>
          <select
            value={form.profile_quality}
            onChange={e => set('profile_quality', e.target.value)}
            className="border rounded px-3 py-2 bg-white"
          >
            <option value="">Default</option>
            <option value="average">Average</option>
            <option value="best">Best</option>
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium">Optimization preference</label>
        <select
          value={form.optimization_preference}
          onChange={e => set('optimization_preference', e.target.value)}
          className="border rounded px-3 py-2 bg-white"
        >
          {PREFERENCES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.include_schedule}
          onChange={e => set('include_schedule', e.target.checked)}
        />
        Include full amortization schedule
      </label>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-black text-white px-6 py-3 font-medium hover:bg-gray-800 transition-colors disabled:opacity-50"
      >
        {loading ? 'Running…' : 'Run simulation'}
      </button>
    </form>
  )
}
