// Single source of truth for frontend-side constants.
// Backend mirrors are in api/constants.py and src/credit_simulator/config.py.

export const API_BASE: string = process.env.NEXT_PUBLIC_API_URL ?? ''

export const SESSION_RESULT_KEY = 'simulator_result'
export const SESSION_INPUTS_KEY = 'simulator_inputs'
export const SESSION_CLONE_KEY = 'simulator_clone'
export const LOCALE_STORAGE_KEY = 'locale'
export const TOUR_DONE_KEY = 'credit_simulator_tour_done'

export const COUNTRIES = ['BE', 'FR', 'DE', 'ES', 'IT', 'PT', 'GB', 'US'] as const
export type Country = (typeof COUNTRIES)[number]

export const OPTIMIZATION_PREFERENCES = [
  'balanced',
  'minimize_total_cost',
  'minimize_monthly_payment',
  'minimize_duration',
  'minimize_down_payment',
] as const
export type OptimizationPreference = (typeof OPTIMIZATION_PREFERENCES)[number]

export const PROFILE_QUALITIES = ['average', 'best'] as const
export type ProfileQuality = (typeof PROFILE_QUALITIES)[number]

export const CURRENCY_DISPLAY_OPTIONS = ['symbol', 'code'] as const
export type CurrencyDisplay = (typeof CURRENCY_DISPLAY_OPTIONS)[number]

export const DEFAULT_COUNTRY: Country = 'BE'
export const DEFAULT_OPTIMIZATION_PREFERENCE: OptimizationPreference = 'balanced'
export const DEFAULT_CURRENCY_DISPLAY: CurrencyDisplay = 'symbol'
export const DEFAULT_CURRENCY_SYMBOL = '€'

export const SUPPORTED_LOCALES = ['en', 'fr'] as const
export type Locale = (typeof SUPPORTED_LOCALES)[number]
