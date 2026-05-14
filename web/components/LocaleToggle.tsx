'use client'

import { useI18n } from '@/lib/i18n'

export function LocaleToggle() {
  const { locale, toggle, t } = useI18n()
  return (
    <button
      onClick={toggle}
      className="text-xs text-gray-400 hover:text-gray-600 transition-colors font-mono"
      aria-label={t('nav.toggle_lang')}
    >
      {locale === 'en' ? 'FR' : 'EN'}
    </button>
  )
}
