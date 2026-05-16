'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { LOCALE_STORAGE_KEY, type Locale } from './constants'

const TRANSLATIONS = {
  en: {
    // Navigation
    'nav.title': 'Credit Simulator',
    'nav.run': 'Run simulation',
    'nav.history': 'My simulations',
    'nav.signin': 'Sign in to save results',
    'nav.preferences': 'Preferences',
    'nav.settings': 'API Keys',
    'nav.home': '← Home',
    'nav.api_docs': 'API docs',
    'nav.toggle_lang': 'Toggle language',
    // Home
    'home.tagline':
      'Find the optimal mortgage plan for your property purchase — down-payment analysis, amortization schedule, and sweet-spot breakdown.',
    // History
    'history.title': 'My simulations',
    'history.new': 'New simulation',
    'history.empty': 'No saved simulations yet.',
    'history.first': 'Run your first simulation',
    'history.view': 'View',
    'history.delete': 'Delete',
    'history.loading': 'Loading…',
    'history.duration_auto': 'auto',
    'history.edit': 'Edit',
    'history.save': 'Save',
    'history.cancel': 'Cancel',
    'history.name_placeholder': 'Simulation name',
    'history.tags_placeholder': 'Tags (comma-separated)',
    // Stats cards
    'stats.total': 'Total simulations',
    'stats.avg_monthly': 'Avg. monthly payment',
    'stats.avg_duration': 'Avg. duration',
    'stats.total_principal': 'Total principal',
    'stats.months': 'months',
    // Preferences
    'prefs.title': 'Preferences',
    'prefs.country': 'Default country',
    'prefs.preference': 'Optimization preference',
    'prefs.currency_display': 'Currency display',
    'prefs.symbol': 'Symbol (€, £, $)',
    'prefs.code': 'Code (EUR, GBP, USD)',
    'prefs.save': 'Save',
    'prefs.saved': 'Saved!',
    'prefs.loading': 'Loading preferences…',
    // Settings / API keys
    'settings.title': 'API Keys',
    'settings.desc': 'Use API keys to call the simulator API programmatically without signing in.',
    'settings.no_keys': 'No API keys yet.',
    'settings.create': 'Create key',
    'settings.name_placeholder': 'Key name (e.g. my-script)',
    'settings.generate': 'Generate',
    'settings.revoke': 'Revoke',
    'settings.created': 'Created',
    'settings.last_used': 'Last used',
    'settings.never': 'Never',
    'settings.copy': 'Copy',
    'settings.copied': 'Copied!',
    'settings.key_warning': 'Copy your key now — it will not be shown again.',
    // Auth
    'auth.title': 'Sign in',
    'auth.email_placeholder': 'you@example.com',
    'auth.send': 'Send magic link',
    'auth.check_inbox': 'Check your inbox for the sign-in link.',
    // Simulate page
    'simulate.title': 'Run a simulation',
    'simulate.subtitle': 'Enter your financial details to find the optimal loan plan.',
    // Form
    'form.property_price': 'Property price',
    'form.monthly_net_income': 'Monthly net income',
    'form.available_savings': 'Available savings',
    'form.country': 'Country',
    'form.country_auto': 'Auto-detect',
    'form.profile_quality': 'Profile quality',
    'form.profile_default': 'Default',
    'form.profile_average': 'Average',
    'form.profile_best': 'Best',
    'form.optimization_preference': 'Optimization preference',
    'form.include_schedule': 'Include full amortization schedule',
    'form.submit': 'Run simulation',
    'form.submitting': 'Running…',
    'form.error_generic': 'Unexpected error — is the API running?',
    // Optimization preferences
    'pref.balanced': 'Balanced',
    'pref.minimize_total_cost': 'Minimize total cost',
    'pref.minimize_monthly_payment': 'Minimize monthly payment',
    'pref.minimize_duration': 'Minimize duration',
    'pref.minimize_down_payment': 'Minimize down payment',
    // Results page
    'results.title': 'Simulation results',
    'results.new': 'New simulation',
    'results.optimal_plan': 'Optimal loan plan',
    'results.profile_suffix': 'profile',
    'results.property_price': 'Property price',
    'results.down_payment': 'Down payment',
    'results.loan_principal': 'Loan principal',
    'results.duration': 'Duration',
    'results.monthly_installment': 'Monthly installment',
    'results.interest_rate': 'Interest rate',
    'results.total_interest': 'Total interest',
    'results.total_insurance': 'Total insurance',
    'results.total_cost': 'Total cost of credit',
    'results.sweet_spot_title': 'Down-payment sweet-spot',
    'results.no_results': 'No results yet.',
    'results.export_csv': 'Export schedule (CSV)',
    // Sweet-spot table headers
    'sweet.down_payment': 'Down payment',
    'sweet.label': 'Label',
    'sweet.monthly': 'Monthly',
    'sweet.total_cost': 'Total cost',
    'sweet.net_saving': 'Net saving',
    'sweet.ltv': 'LTV',
    'sweet.rate': 'Rate',
    // Amortization table
    'amort.show': 'Show amortization schedule',
    'amort.hide': 'Hide amortization schedule',
    'amort.month': 'Month',
    'amort.opening': 'Opening',
    'amort.interest': 'Interest',
    'amort.principal': 'Principal',
    'amort.insurance': 'Insurance',
    'amort.total': 'Total',
    'amort.closing': 'Closing',
    // Loan chart
    'chart.balance_title': 'Outstanding balance over time',
    'chart.month_axis': 'Month',
    // Errors
    'error.generic': 'Something went wrong.',
    // What-if panel
    'whatif.title': 'What-if tweaking',
    'whatif.rate': 'Interest rate',
    'whatif.duration': 'Duration (months)',
    'whatif.down_payment': 'Down payment',
    'whatif.loading': 'Recalculating…',
    'whatif.error': 'Could not recalculate — check your inputs.',
    'whatif.reset': 'Reset',
    'whatif.original': 'Original',
    'whatif.tweaked': 'Tweaked',
    'whatif.delta': 'Delta',
    'whatif.monthly': 'Monthly installment',
    'whatif.total_interest': 'Total interest',
    'whatif.total_cost': 'Total cost',
  },
  fr: {
    // Navigation
    'nav.title': 'Simulateur de crédit',
    'nav.run': 'Lancer une simulation',
    'nav.history': 'Mes simulations',
    'nav.signin': 'Se connecter pour sauvegarder',
    'nav.preferences': 'Préférences',
    'nav.settings': 'Clés API',
    'nav.home': '← Accueil',
    'nav.api_docs': 'Docs API',
    'nav.toggle_lang': 'Changer de langue',
    // Home
    'home.tagline':
      "Trouvez le plan de prêt optimal pour votre achat immobilier — analyse de l'apport, tableau d'amortissement et point optimal.",
    // History
    'history.title': 'Mes simulations',
    'history.new': 'Nouvelle simulation',
    'history.empty': 'Aucune simulation sauvegardée.',
    'history.first': 'Lancer votre première simulation',
    'history.view': 'Voir',
    'history.delete': 'Supprimer',
    'history.loading': 'Chargement…',
    'history.duration_auto': 'auto',
    'history.edit': 'Modifier',
    'history.save': 'Enregistrer',
    'history.cancel': 'Annuler',
    'history.name_placeholder': 'Nom de la simulation',
    'history.tags_placeholder': 'Étiquettes (séparées par des virgules)',
    // Stats cards
    'stats.total': 'Simulations totales',
    'stats.avg_monthly': 'Mensualité moy.',
    'stats.avg_duration': 'Durée moy.',
    'stats.total_principal': 'Capital total',
    'stats.months': 'mois',
    // Preferences
    'prefs.title': 'Préférences',
    'prefs.country': 'Pays par défaut',
    'prefs.preference': "Préférence d'optimisation",
    'prefs.currency_display': 'Affichage devise',
    'prefs.symbol': 'Symbole (€, £, $)',
    'prefs.code': 'Code (EUR, GBP, USD)',
    'prefs.save': 'Enregistrer',
    'prefs.saved': 'Enregistré !',
    'prefs.loading': 'Chargement des préférences…',
    // Settings / API keys
    'settings.title': 'Clés API',
    'settings.desc':
      "Utilisez des clés API pour appeler l'API du simulateur de façon programmatique sans vous connecter.",
    'settings.no_keys': 'Aucune clé API.',
    'settings.create': 'Créer une clé',
    'settings.name_placeholder': 'Nom de la clé (ex. mon-script)',
    'settings.generate': 'Générer',
    'settings.revoke': 'Révoquer',
    'settings.created': 'Créée',
    'settings.last_used': 'Dernière utilisation',
    'settings.never': 'Jamais',
    'settings.copy': 'Copier',
    'settings.copied': 'Copié !',
    'settings.key_warning': 'Copiez votre clé maintenant — elle ne sera plus affichée.',
    // Auth
    'auth.title': 'Se connecter',
    'auth.email_placeholder': 'vous@exemple.com',
    'auth.send': 'Envoyer le lien magique',
    'auth.check_inbox': 'Vérifiez votre boîte mail pour le lien de connexion.',
    // Simulate page
    'simulate.title': 'Lancer une simulation',
    'simulate.subtitle': 'Saisissez vos détails financiers pour trouver le plan de prêt optimal.',
    // Form
    'form.property_price': 'Prix du bien',
    'form.monthly_net_income': 'Revenu net mensuel',
    'form.available_savings': 'Épargne disponible',
    'form.country': 'Pays',
    'form.country_auto': 'Auto-détection',
    'form.profile_quality': 'Qualité du profil',
    'form.profile_default': 'Par défaut',
    'form.profile_average': 'Moyenne',
    'form.profile_best': 'Meilleure',
    'form.optimization_preference': "Préférence d'optimisation",
    'form.include_schedule': "Inclure le tableau d'amortissement complet",
    'form.submit': 'Lancer la simulation',
    'form.submitting': 'Calcul en cours…',
    'form.error_generic': "Erreur inattendue — l’API est-elle démarrée ?",
    // Optimization preferences
    'pref.balanced': 'Équilibré',
    'pref.minimize_total_cost': 'Minimiser le coût total',
    'pref.minimize_monthly_payment': 'Minimiser la mensualité',
    'pref.minimize_duration': 'Minimiser la durée',
    'pref.minimize_down_payment': "Minimiser l'apport",
    // Results page
    'results.title': 'Résultats de la simulation',
    'results.new': 'Nouvelle simulation',
    'results.optimal_plan': 'Plan de prêt optimal',
    'results.profile_suffix': 'profil',
    'results.property_price': 'Prix du bien',
    'results.down_payment': 'Apport',
    'results.loan_principal': 'Capital emprunté',
    'results.duration': 'Durée',
    'results.monthly_installment': 'Mensualité',
    'results.interest_rate': "Taux d'intérêt",
    'results.total_interest': 'Intérêts totaux',
    'results.total_insurance': 'Assurance totale',
    'results.total_cost': 'Coût total du crédit',
    'results.sweet_spot_title': 'Apport optimal',
    'results.no_results': 'Aucun résultat pour le moment.',
    'results.export_csv': 'Exporter le tableau (CSV)',
    // Sweet-spot table headers
    'sweet.down_payment': 'Apport',
    'sweet.label': 'Libellé',
    'sweet.monthly': 'Mensualité',
    'sweet.total_cost': 'Coût total',
    'sweet.net_saving': 'Économie nette',
    'sweet.ltv': 'LTV',
    'sweet.rate': 'Taux',
    // Amortization table
    'amort.show': "Afficher le tableau d'amortissement",
    'amort.hide': "Masquer le tableau d'amortissement",
    'amort.month': 'Mois',
    'amort.opening': 'Solde initial',
    'amort.interest': 'Intérêts',
    'amort.principal': 'Capital',
    'amort.insurance': 'Assurance',
    'amort.total': 'Total',
    'amort.closing': 'Solde final',
    // Loan chart
    'chart.balance_title': 'Solde restant au fil du temps',
    'chart.month_axis': 'Mois',
    // Errors
    'error.generic': "Une erreur s'est produite.",
    // What-if panel
    'whatif.title': 'Simulation what-if',
    'whatif.rate': "Taux d'intérêt",
    'whatif.duration': 'Durée (mois)',
    'whatif.down_payment': 'Apport',
    'whatif.loading': 'Recalcul en cours…',
    'whatif.error': 'Impossible de recalculer — vérifiez vos valeurs.',
    'whatif.reset': 'Réinitialiser',
    'whatif.original': 'Original',
    'whatif.tweaked': 'Modifié',
    'whatif.delta': 'Delta',
    'whatif.monthly': 'Mensualité',
    'whatif.total_interest': 'Intérêts totaux',
    'whatif.total_cost': 'Coût total',
  },
} satisfies Record<Locale, Record<string, string>>

export type TranslationKey = keyof (typeof TRANSLATIONS)['en']

interface I18nContextValue {
  locale: Locale
  t: (key: TranslationKey) => string
  toggle: () => void
}

const I18nContext = createContext<I18nContextValue | null>(null)

function detectLocale(): Locale {
  if (typeof window === 'undefined') return 'en'
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
  if (stored === 'fr' || stored === 'en') return stored
  const lang = navigator.language.toLowerCase()
  return lang.startsWith('fr') ? 'fr' : 'en'
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<Locale>('en')

  useEffect(() => {
    setLocale(detectLocale())
  }, [])

  const t = (key: TranslationKey): string =>
    TRANSLATIONS[locale][key] ?? TRANSLATIONS['en'][key] ?? key

  const toggle = () => {
    const next: Locale = locale === 'en' ? 'fr' : 'en'
    setLocale(next)
    localStorage.setItem(LOCALE_STORAGE_KEY, next)
  }

  return <I18nContext.Provider value={{ locale, t, toggle }}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used inside I18nProvider')
  return ctx
}
