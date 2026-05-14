'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import { getPreferences, updatePreferences, ApiError, UserPreferences } from '@/lib/api'
import {
  COUNTRIES,
  CURRENCY_DISPLAY_OPTIONS,
  DEFAULT_COUNTRY,
  DEFAULT_CURRENCY_DISPLAY,
  DEFAULT_OPTIMIZATION_PREFERENCE,
  OPTIMIZATION_PREFERENCES,
} from '@/lib/constants'
import { useI18n, type TranslationKey } from '@/lib/i18n'
import { LocaleToggle } from '@/components/LocaleToggle'

const PREFERENCE_LABEL_KEY: Record<(typeof OPTIMIZATION_PREFERENCES)[number], TranslationKey> = {
  balanced: 'pref.balanced',
  minimize_total_cost: 'pref.minimize_total_cost',
  minimize_monthly_payment: 'pref.minimize_monthly_payment',
  minimize_duration: 'pref.minimize_duration',
  minimize_down_payment: 'pref.minimize_down_payment',
}

export default function PreferencesPage() {
  const router = useRouter()
  const { t } = useI18n()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [form, setForm] = useState<UserPreferences>({
    default_country: DEFAULT_COUNTRY,
    default_optimization_preference: DEFAULT_OPTIMIZATION_PREFERENCE,
    currency_display: DEFAULT_CURRENCY_DISPLAY,
  })

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session) { router.replace('/auth'); return }
      try {
        const prefs = await getPreferences(session.access_token)
        setForm(prefs)
      } catch {
        // defaults already set
      } finally {
        setLoading(false)
      }
    })
  }, [router])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    setSaving(true)
    setError(null)
    try {
      const updated = await updatePreferences(form, session.access_token)
      setForm(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">{t('prefs.loading')}</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen p-8 max-w-lg mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('prefs.title')}</h1>
        <LocaleToggle />
      </div>

      {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

      <form onSubmit={handleSave} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('prefs.country')}
          </label>
          <select
            value={form.default_country}
            onChange={e => setForm(f => ({ ...f, default_country: e.target.value }))}
            className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
          >
            {COUNTRIES.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('prefs.preference')}
          </label>
          <select
            value={form.default_optimization_preference}
            onChange={e => setForm(f => ({ ...f, default_optimization_preference: e.target.value }))}
            className="w-full rounded-lg border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-black"
          >
            {OPTIMIZATION_PREFERENCES.map(p => (
              <option key={p} value={p}>{t(PREFERENCE_LABEL_KEY[p])}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('prefs.currency_display')}
          </label>
          <div className="flex gap-4">
            {CURRENCY_DISPLAY_OPTIONS.map(opt => (
              <label key={opt} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="currency_display"
                  value={opt}
                  checked={form.currency_display === opt}
                  onChange={() => setForm(f => ({ ...f, currency_display: opt }))}
                  className="accent-black"
                />
                <span className="text-sm">{t(opt === 'symbol' ? 'prefs.symbol' : 'prefs.code')}</span>
              </label>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-lg bg-black text-white py-2.5 font-medium hover:bg-gray-800 transition-colors disabled:opacity-50"
        >
          {saved ? t('prefs.saved') : saving ? '…' : t('prefs.save')}
        </button>
      </form>

      <div className="mt-8 text-center">
        <Link href="/" className="text-sm text-gray-400 hover:text-gray-600">{t('nav.home')}</Link>
      </div>
    </main>
  )
}
