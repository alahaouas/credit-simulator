'use client'

import Link from 'next/link'
import { useI18n } from '@/lib/i18n'

export function LegalFooter() {
  const { t } = useI18n()
  return (
    <footer className="py-4 text-center text-xs text-gray-400 dark:text-gray-500 print:hidden">
      <Link href="/legal" className="underline hover:text-gray-600 dark:hover:text-gray-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded">
        {t('legal.link')}
      </Link>
    </footer>
  )
}
