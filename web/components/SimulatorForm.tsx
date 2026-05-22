'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { simulate, getProfile, refreshRate, SimulateRequest, ApiError } from '@/lib/api'
import {
  COUNTRIES,
  OPTIMIZATION_PREFERENCES,
  DEFAULT_OPTIMIZATION_PREFERENCE,
  SESSION_RESULT_KEY,
  SESSION_INPUTS_KEY,
  SESSION_CLONE_KEY,
  type ProfileQuality,
} from '@/lib/constants'
import { useI18n, type TranslationKey } from '@/lib/i18n'
import { useTour } from '@/hooks/useTour'
import TourTooltip from '@/components/TourTooltip'

const PREFERENCE_LABEL_KEY: Record<(typeof OPTIMIZATION_PREFERENCES)[number], TranslationKey> = {
  balanced: 'pref.balanced',
  minimize_total_cost: 'pref.minimize_total_cost',
  minimize_monthly_payment: 'pref.minimize_monthly_payment',
  minimize_duration: 'pref.minimize_duration',
  minimize_down_payment: 'pref.minimize_down_payment',
}

const inputClass = 'border dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-gray-400'
const selectClass = 'border dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-gray-400'

interface ProfileOverrides {
  annual_interest_rate_pct: string
  insurance_rate_pct: string
  min_down_pct: string
  max_debt_pct: string
  max_duration_months: string
}

const EMPTY_OVERRIDES: ProfileOverrides = {
  annual_interest_rate_pct: '',
  insurance_rate_pct: '',
  min_down_pct: '',
  max_debt_pct: '',
  max_duration_months: '',
}

function pctToFraction(pct: string): string | undefined {
  if (!pct.trim()) return undefined
  const n = parseFloat(pct)
  if (isNaN(n)) return undefined
  return String(n / 100)
}

function overridesKey(country: string) {
  return `profile_overrides_${country}`
}

export default function SimulatorForm() {
  const router = useRouter()
  const { t } = useI18n()
  const { step, totalSteps, next, skip, restart, done } = useTour()
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

  // C4 — custom profile overrides
  const [overrides, setOverrides] = useState<ProfileOverrides>(EMPTY_OVERRIDES)
  const [showCustomProfile, setShowCustomProfile] = useState(false)
  const [loadingProfile, setLoadingProfile] = useState(false)

  // C3 — live rate
  const [liveRatePct, setLiveRatePct] = useState<string | null>(null)
  const [refreshingRate, setRefreshingRate] = useState(false)
  const [refreshRateError, setRefreshRateError] = useState(false)

  // Restore clone data
  useEffect(() => {
    const raw = sessionStorage.getItem(SESSION_CLONE_KEY)
    if (!raw) return
    sessionStorage.removeItem(SESSION_CLONE_KEY)
    try {
      const inputs = JSON.parse(raw)
      setForm(f => ({
        ...f,
        property_price: inputs.property_price ?? f.property_price,
        monthly_net_income: inputs.monthly_net_income ?? f.monthly_net_income,
        available_savings: inputs.available_savings ?? f.available_savings,
        country: inputs.country ?? f.country,
        profile_quality: inputs.profile_quality ?? f.profile_quality,
        optimization_preference: inputs.optimization_preference ?? f.optimization_preference,
        include_schedule: inputs.include_schedule ?? f.include_schedule,
      }))
    } catch {
      // ignore malformed clone data
    }
  }, [])

  // C4 — load profile when country changes
  useEffect(() => {
    setLiveRatePct(null)
    setRefreshRateError(false)
    if (!form.country) {
      setOverrides(EMPTY_OVERRIDES)
      return
    }
    // Try sessionStorage first
    const stored = sessionStorage.getItem(overridesKey(form.country))
    if (stored) {
      try { setOverrides(JSON.parse(stored)); return } catch { /* ignore malformed */ }
    }
    // Fetch profile defaults
    setLoadingProfile(true)
    getProfile(form.country)
      .then(p => {
        const next: ProfileOverrides = {
          annual_interest_rate_pct: (parseFloat(p.annual_rate_average) * 100).toFixed(4),
          insurance_rate_pct: (parseFloat(p.insurance_rate_average) * 100).toFixed(4),
          min_down_pct: (parseFloat(p.min_down_payment_ratio) * 100).toFixed(2),
          max_debt_pct: (parseFloat(p.max_debt_ratio) * 100).toFixed(2),
          max_duration_months: String(p.max_loan_duration_months),
        }
        setOverrides(next)
        sessionStorage.setItem(overridesKey(form.country), JSON.stringify(next))
      })
      .catch(() => { /* ignore fetch errors */ })
      .finally(() => setLoadingProfile(false))
  }, [form.country])

  function set(field: string, value: string | boolean) {
    setForm(f => ({ ...f, [field]: value }))
  }

  function setOverride(field: keyof ProfileOverrides, value: string) {
    setOverrides(prev => {
      const next = { ...prev, [field]: value }
      if (form.country) sessionStorage.setItem(overridesKey(form.country), JSON.stringify(next))
      return next
    })
  }

  function resetOverrides() {
    if (!form.country) return
    sessionStorage.removeItem(overridesKey(form.country))
    setOverrides(EMPTY_OVERRIDES)
    // Re-trigger profile load
    setLoadingProfile(true)
    getProfile(form.country)
      .then(p => {
        const next: ProfileOverrides = {
          annual_interest_rate_pct: (parseFloat(p.annual_rate_average) * 100).toFixed(4),
          insurance_rate_pct: (parseFloat(p.insurance_rate_average) * 100).toFixed(4),
          min_down_pct: (parseFloat(p.min_down_payment_ratio) * 100).toFixed(2),
          max_debt_pct: (parseFloat(p.max_debt_ratio) * 100).toFixed(2),
          max_duration_months: String(p.max_loan_duration_months),
        }
        setOverrides(next)
        sessionStorage.setItem(overridesKey(form.country), JSON.stringify(next))
      })
      .catch(() => { /* ignore fetch errors */ })
      .finally(() => setLoadingProfile(false))
  }

  // C3 — refresh live rate
  async function handleRefreshRate() {
    if (!form.country) return
    setRefreshingRate(true)
    setRefreshRateError(false)
    setLiveRatePct(null)
    try {
      const res = await refreshRate(form.country)
      const pct = (parseFloat(res.annual_rate_average) * 100).toFixed(4)
      setLiveRatePct(pct)
      setOverride('annual_interest_rate_pct', pct)
    } catch {
      setRefreshRateError(true)
    } finally {
      setRefreshingRate(false)
    }
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
      // C4 — apply non-default overrides only when a country is selected
      if (form.country && showCustomProfile) {
        const frac = pctToFraction(overrides.annual_interest_rate_pct)
        if (frac) req.annual_interest_rate = frac
        const ins = pctToFraction(overrides.insurance_rate_pct)
        if (ins) req.insurance_rate = ins
        const minDown = pctToFraction(overrides.min_down_pct)
        if (minDown) req.min_down_payment_ratio = minDown
        const maxDebt = pctToFraction(overrides.max_debt_pct)
        if (maxDebt) req.max_debt_ratio = maxDebt
        const dur = parseInt(overrides.max_duration_months)
        if (!isNaN(dur) && dur > 0) req.max_loan_duration_months = dur
      }
      const result = await simulate(req)
      sessionStorage.setItem(SESSION_RESULT_KEY, JSON.stringify(result))
      sessionStorage.setItem(SESSION_INPUTS_KEY, JSON.stringify(req))
      router.push('/results')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('form.error_generic'))
    } finally {
      setLoading(false)
    }
  }

  const tourProps = (tourStep: number) => ({
    active: step === tourStep,
    step: tourStep,
    total: totalSteps,
    nextLabel: tourStep === totalSteps - 1 ? t('tour.done') : t('tour.next'),
    skipLabel: t('tour.skip'),
    onNext: next,
    onSkip: skip,
  })

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-5 w-full max-w-lg">
      <TourTooltip title={t('tour.step1_title')} description={t('tour.step1_desc')} {...tourProps(0)}>
        <div className="flex flex-col gap-1">
          <label htmlFor="property_price" className="text-sm font-medium">{t('form.property_price')}</label>
          <input
            id="property_price"
            type="number" min="0" step="any" required
            placeholder="300000"
            value={form.property_price}
            onChange={e => set('property_price', e.target.value)}
            className={inputClass}
          />
        </div>
      </TourTooltip>

      <TourTooltip title={t('tour.step2_title')} description={t('tour.step2_desc')} {...tourProps(1)}>
        <div className="flex flex-col gap-1">
          <label htmlFor="monthly_net_income" className="text-sm font-medium">{t('form.monthly_net_income')}</label>
          <input
            id="monthly_net_income"
            type="number" min="0" step="any" required
            placeholder="3500"
            value={form.monthly_net_income}
            onChange={e => set('monthly_net_income', e.target.value)}
            className={inputClass}
          />
        </div>
      </TourTooltip>

      <TourTooltip title={t('tour.step3_title')} description={t('tour.step3_desc')} {...tourProps(2)}>
        <div className="flex flex-col gap-1">
          <label htmlFor="available_savings" className="text-sm font-medium">{t('form.available_savings')}</label>
          <input
            id="available_savings"
            type="number" min="0" step="any" required
            placeholder="60000"
            value={form.available_savings}
            onChange={e => set('available_savings', e.target.value)}
            className={inputClass}
          />
        </div>
      </TourTooltip>

      <TourTooltip title={t('tour.step4_title')} description={t('tour.step4_desc')} {...tourProps(3)}>
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label htmlFor="country" className="text-sm font-medium">{t('form.country')}</label>
              <select
                id="country"
                value={form.country}
                onChange={e => set('country', e.target.value)}
                className={selectClass}
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
                className={selectClass}
              >
                <option value="">{t('form.profile_default')}</option>
                <option value="average">{t('form.profile_average')}</option>
                <option value="best">{t('form.profile_best')}</option>
              </select>
            </div>
          </div>

          {/* C3 — Live rate refresh */}
          {form.country && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleRefreshRate}
                disabled={refreshingRate}
                className="text-xs text-gray-500 dark:text-gray-400 hover:text-black dark:hover:text-white disabled:opacity-40 transition-colors border dark:border-gray-600 rounded px-2 py-1"
              >
                {refreshingRate ? t('profile.refreshing') : t('profile.refresh_rate')}
              </button>
              {liveRatePct && (
                <span className="text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded px-2 py-0.5">
                  {t('profile.live_badge')}: {liveRatePct}%
                </span>
              )}
              {refreshRateError && (
                <span className="text-xs text-red-500">{t('profile.refresh_error')}</span>
              )}
            </div>
          )}

          {/* C4 — Custom profile overrides */}
          {form.country && (
            <details
              open={showCustomProfile}
              onToggle={e => setShowCustomProfile((e.currentTarget as HTMLDetailsElement).open)}
            >
              <summary className="text-sm font-medium cursor-pointer text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 select-none">
                {t('profile.customize')}
                {showCustomProfile ? ' ▲' : ' ▼'}
              </summary>
              <div className="mt-3 flex flex-col gap-3">
                {loadingProfile ? (
                  <p className="text-xs text-gray-400">{t('profile.loading')}</p>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400">{t('profile.annual_rate')}</label>
                        <input
                          type="number" min="0" max="99" step="0.0001"
                          value={overrides.annual_interest_rate_pct}
                          onChange={e => setOverride('annual_interest_rate_pct', e.target.value)}
                          className={`${inputClass} text-sm`}
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400">{t('profile.insurance_rate')}</label>
                        <input
                          type="number" min="0" max="99" step="0.0001"
                          value={overrides.insurance_rate_pct}
                          onChange={e => setOverride('insurance_rate_pct', e.target.value)}
                          className={`${inputClass} text-sm`}
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400">{t('profile.min_down')}</label>
                        <input
                          type="number" min="0" max="100" step="0.01"
                          value={overrides.min_down_pct}
                          onChange={e => setOverride('min_down_pct', e.target.value)}
                          className={`${inputClass} text-sm`}
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400">{t('profile.max_debt')}</label>
                        <input
                          type="number" min="0" max="100" step="0.01"
                          value={overrides.max_debt_pct}
                          onChange={e => setOverride('max_debt_pct', e.target.value)}
                          className={`${inputClass} text-sm`}
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-xs font-medium text-gray-600 dark:text-gray-400">{t('profile.max_duration')}</label>
                        <input
                          type="number" min="1" max="600" step="1"
                          value={overrides.max_duration_months}
                          onChange={e => setOverride('max_duration_months', e.target.value)}
                          className={`${inputClass} text-sm`}
                        />
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={resetOverrides}
                      className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-left"
                    >
                      {t('profile.reset')}
                    </button>
                  </>
                )}
              </div>
            </details>
          )}
        </div>
      </TourTooltip>

      <TourTooltip title={t('tour.step5_title')} description={t('tour.step5_desc')} {...tourProps(4)}>
        <div className="flex flex-col gap-1">
          <label htmlFor="optimization_preference" className="text-sm font-medium">{t('form.optimization_preference')}</label>
          <select
            id="optimization_preference"
            value={form.optimization_preference}
            onChange={e => set('optimization_preference', e.target.value)}
            className={selectClass}
          >
            {OPTIMIZATION_PREFERENCES.map(p => (
              <option key={p} value={p}>{t(PREFERENCE_LABEL_KEY[p])}</option>
            ))}
          </select>
        </div>
      </TourTooltip>

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
        aria-label={loading ? t('aria.loading') : t('form.submit')}
        className="flex items-center justify-center min-h-[48px] rounded-lg bg-black text-white dark:bg-white dark:text-black px-6 py-3 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900"
      >
        {loading ? (
          <svg aria-hidden="true" className="animate-spin h-5 w-5 text-white dark:text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        ) : (
          t('form.submit')
        )}
      </button>

      {done && (
        <button
          type="button"
          onClick={restart}
          className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-center"
        >
          {t('tour.restart')}
        </button>
      )}
    </form>
  )
}
