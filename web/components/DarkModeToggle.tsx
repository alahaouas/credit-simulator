'use client'

import { useTheme } from './ThemeProvider'

export function DarkModeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button
      onClick={toggle}
      className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors font-mono"
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {theme === 'dark' ? 'Light' : 'Dark'}
    </button>
  )
}
