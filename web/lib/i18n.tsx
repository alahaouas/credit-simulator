'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'

type Locale = 'en' | 'fr'

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
    // Errors
    'error.generic': 'Something went wrong.',
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
    // Errors
    'error.generic': 'Une erreur s\'est produite.',
  },
} satisfies Record<Locale, Record<string, string>>

type TranslationKey = keyof (typeof TRANSLATIONS)['en']

interface I18nContextValue {
  locale: Locale
  t: (key: TranslationKey) => string
  toggle: () => void
}

const I18nContext = createContext<I18nContextValue | null>(null)

function detectLocale(): Locale {
  if (typeof window === 'undefined') return 'en'
  const stored = localStorage.getItem('locale')
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
    localStorage.setItem('locale', next)
  }

  return <I18nContext.Provider value={{ locale, t, toggle }}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used inside I18nProvider')
  return ctx
}
