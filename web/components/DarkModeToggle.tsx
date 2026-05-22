'use client'

import { useTheme } from './ThemeProvider'

export function DarkModeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button
      onClick={toggle}
      className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded px-1 py-0.5"
      aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {theme === 'dark' ? 'Light' : 'Dark'}
    </button>
  )
}
