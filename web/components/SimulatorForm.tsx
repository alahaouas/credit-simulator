'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { simulate, SimulateRequest, ApiError } from '@/lib/api'
import {
  COUNTRIES,
  OPTIMIZATION_PREFERENCES,
  DEFAULT_OPTIMIZATION_PREFERENCE,
  SESSION_RESULT_KEY,
  type ProfileQuality,
} from '@/lib/constants'
import { useI18n, type TranslationKey } from '@/lib/i18n'

const PREFERENCE_LABEL_KEY: Record<(typeof OPTIMIZATION_PREFERENCES)[number], TranslationKey> = {
  balanced: 'pref.balanced',
  minimize_total_cost: 'pref.minimize_total_cost',
  minimize_monthly_payment: 'pref.minimize_monthly_payment',
  minimize_duration: 'pref.minimize_duration',
  minimize_down_payment: 'pref.minimize_down_payment',
}

export default function SimulatorForm() {
  const router = useRouter()
  const { t } = useI18n()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState({
    property_price: '',
    monthly_net_income: '',
    available_savings: '',
    country: '',
    profile_quality: '',
    optimization_preference: DEFAULT_OPTIMIZATION_PREFERENCE as string,
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
        ...(form.profile_quality && { profile_quality: form.profile_quality as ProfileQuality }),
      }
      const result = await simulate(req)
      sessionStorage.setItem(SESSION_RESULT_KEY, JSON.stringify(result))
      router.push('/results')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('form.error_generic'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5 w-full max-w-lg">
      <div className="flex flex-col gap-1">
        <label htmlFor="property_price" className="text-sm font-medium">{t('form.property_price')}</label>
        <input
          id="property_price"
          type="number" min="0" step="any" required
          placeholder="300000"
          value={form.property_price}
          onChange={e => set('property_price', e.target.value)}
          className="border rounded px-3 py-2"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="monthly_net_income" className="text-sm font-medium">{t('form.monthly_net_income')}</label>
        <input
          id="monthly_net_income"
          type="number" min="0" step="any" required
          placeholder="3500"
          value={form.monthly_net_income}
          onChange={e => set('monthly_net_income', e.target.value)}
          className="border rounded px-3 py-2"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="available_savings" className="text-sm font-medium">{t('form.available_savings')}</label>
        <input
          id="available_savings"
          type="number" min="0" step="any" required
          placeholder="60000"
          value={form.available_savings}
          onChange={e => set('available_savings', e.target.value)}
          className="border rounded px-3 py-2"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label htmlFor="country" className="text-sm font-medium">{t('form.country')}</label>
          <select
            id="country"
            value={form.country}
            onChange={e => set('country', e.target.value)}
            className="border rounded px-3 py-2 bg-white"
          >
            <option value="">{t('form.country_auto')}</option>
            {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="profile_quality" className="text-sm font-medium">{t('form.profile_quality')}</label>
          <select
            id="profile_quality"
            value={form.profile_quality}
            onChange={e => set('profile_quality', e.target.value)}
            className="border rounded px-3 py-2 bg-white"
          >
            <option value="">{t('form.profile_default')}</option>
            <option value="average">{t('form.profile_average')}</option>
            <option value="best">{t('form.profile_best')}</option>
          </select>
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="optimization_preference" className="text-sm font-medium">{t('form.optimization_preference')}</label>
        <select
          id="optimization_preference"
          value={form.optimization_preference}
          onChange={e => set('optimization_preference', e.target.value)}
          className="border rounded px-3 py-2 bg-white"
        >
          {OPTIMIZATION_PREFERENCES.map(p => (
            <option key={p} value={p}>{t(PREFERENCE_LABEL_KEY[p])}</option>
          ))}
        </select>
      </div>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.include_schedule}
          onChange={e => set('include_schedule', e.target.checked)}
        />
        {t('form.include_schedule')}
      </label>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="rounded-lg bg-black text-white px-6 py-3 font-medium hover:bg-gray-800 transition-colors disabled:opacity-50"
      >
        {loading ? t('form.submitting') : t('form.submit')}
      </button>
    </form>
  )
}
