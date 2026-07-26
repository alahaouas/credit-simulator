'use client'

import { useTheme } from './ThemeProvider'
import { useI18n } from '@/lib/i18n'

export function DarkModeToggle() {
  const { theme, toggle } = useTheme()
  const { t } = useI18n()
  return (
    <button
      onClick={toggle}
      className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded px-1 py-0.5"
      aria-label={theme === 'dark' ? t('nav.theme_to_light') : t('nav.theme_to_dark')}
    >
      {theme === 'dark' ? t('nav.theme_light') : t('nav.theme_dark')}
    </button>
  )
}
