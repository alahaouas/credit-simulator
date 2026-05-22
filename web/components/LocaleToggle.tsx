'use client'

import { useI18n } from '@/lib/i18n'

export function LocaleToggle() {
  const { locale, toggle, t } = useI18n()
  return (
    <button
      onClick={toggle}
      className="text-xs text-gray-400 hover:text-gray-600 transition-colors font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded px-1 py-0.5"
      aria-label={t('nav.toggle_lang')}
    >
      {locale === 'en' ? 'FR' : 'EN'}
    </button>
  )
}
