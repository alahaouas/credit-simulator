'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import { listAlerts, createAlert, deleteAlert, RateAlert, ApiError } from '@/lib/api'
import { COUNTRIES } from '@/lib/constants'
import { useI18n } from '@/lib/i18n'
import { DarkModeToggle } from '@/components/DarkModeToggle'
import { LocaleToggle } from '@/components/LocaleToggle'

const inputClass =
  'border dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-gray-400'
const selectClass = inputClass

export default function AlertsPage() {
  const { t } = useI18n()
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [alerts, setAlerts] = useState<RateAlert[]>([])
  const [loading, setLoading] = useState(true)
  const [country, setCountry] = useState<string>(COUNTRIES[0])
  const [targetRatePct, setTargetRatePct] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) {
      setLoading(false)
      return
    }
    const supabase = createClient()
    supabase.auth.getSession().then(({ data }) => {
      const token = data.session?.access_token ?? null
      setAccessToken(token)
      if (!token) { setLoading(false); return }
      return listAlerts(token)
        .then(res => setAlerts(res.alerts))
        .catch(() => {})
        .finally(() => setLoading(false))
    })
  }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!accessToken) return
    const pct = parseFloat(targetRatePct)
    if (isNaN(pct) || pct <= 0 || pct >= 100) {
      setCreateError('Enter a rate between 0 and 100.')
      return
    }
    setCreateError(null)
    setCreating(true)
    try {
      const fraction = String(pct / 100)
      const alert = await createAlert(country, fraction, accessToken)
      setAlerts(prev => [alert, ...prev])
      setTargetRatePct('')
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : t('error.generic'))
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm(t('alerts.confirm_delete') || 'Are you sure you want to delete this alert?')) return
    if (!accessToken) return
    setDeletingId(id)
    try {
      await deleteAlert(id, accessToken)
      setAlerts(prev => prev.filter(a => a.id !== id))
    } catch {
      // ignore
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <main className="min-h-screen p-8">
      <div className="absolute top-4 right-4 flex items-center gap-3">
        <DarkModeToggle />
        <LocaleToggle />
      </div>

      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <Link href="/" className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200">
            {t('nav.home')}
          </Link>
        </div>

        <h1 className="text-2xl font-bold tracking-tight mb-1">{t('alerts.title')}</h1>
        <p className="text-gray-500 dark:text-gray-400 mb-6">{t('alerts.subtitle')}</p>

        {!accessToken && !loading ? (
          <p className="text-gray-500 dark:text-gray-400">
            {t('alerts.signin_required')}{' '}
            <Link href="/auth" className="underline">{t('nav.signin')}</Link>
          </p>
        ) : (
          <>
            {/* Create form */}
            <form onSubmit={handleCreate} className="flex gap-3 mb-8 items-end flex-wrap">
              <div className="flex flex-col gap-1">
                <label htmlFor="country" className="text-sm font-medium">{t('alerts.country')}</label>
                <select
                  id="country"
                  value={country}
                  onChange={e => setCountry(e.target.value)}
                  className={selectClass}
                >
                  {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label htmlFor="targetRate" className="text-sm font-medium">{t('alerts.target_rate')}</label>
                <input
                  id="targetRate"
                  type="number"
                  min="0.01"
                  max="99.99"
                  step="0.01"
                  placeholder="3.00"
                  value={targetRatePct}
                  onChange={e => setTargetRatePct(e.target.value)}
                  required
                  className={`${inputClass} w-32`}
                />
              </div>
              <button
                type="submit"
                disabled={creating}
                aria-label={creating ? t('aria.loading') : t('alerts.create')}
                className="rounded-lg bg-black text-white dark:bg-white dark:text-black px-5 py-2 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-50 min-w-[80px] min-h-[40px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900"
              >
                {creating ? (
                  <svg aria-hidden="true" className="animate-spin h-5 w-5 text-white dark:text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  t('alerts.create')
                )}
              </button>
            </form>
            {createError && <p className="text-red-500 text-sm mb-4">{createError}</p>}

            <p className="text-xs text-gray-400 dark:text-gray-500 mb-6">{t('alerts.cron_note')}</p>

            {/* Alert list */}
            {loading ? (
              <p className="text-gray-400">{t('alerts.loading')}</p>
            ) : alerts.length === 0 ? (
              <p className="text-gray-400">{t('alerts.no_alerts')}</p>
            ) : (
              <div className="flex flex-col gap-3">
                {alerts.map(alert => (
                  <div
                    key={alert.id}
                    className="flex items-center justify-between border dark:border-gray-700 rounded-lg px-4 py-3 bg-white dark:bg-gray-800"
                  >
                    <div className="flex flex-col gap-0.5">
                      <span className="font-semibold">
                        {alert.country} — {(parseFloat(alert.target_rate) * 100).toFixed(2)}%
                      </span>
                      <span className="text-xs text-gray-400 dark:text-gray-500">
                        {t('alerts.last_notified')}:{' '}
                        {alert.last_notified_at
                          ? new Date(alert.last_notified_at).toLocaleDateString()
                          : t('alerts.never')}
                      </span>
                    </div>
                    <button
                      onClick={() => handleDelete(alert.id)}
                      disabled={deletingId === alert.id}
                      aria-label={deletingId === alert.id ? t('aria.loading') : t('alerts.delete')}
                      className="text-sm text-red-500 hover:text-red-700 disabled:opacity-40 transition-colors min-h-[32px] flex items-center justify-center min-w-[60px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 rounded"
                    >
                      {deletingId === alert.id ? (
                        <svg aria-hidden="true" className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      ) : (
                        t('alerts.delete')
                      )}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  )
}
