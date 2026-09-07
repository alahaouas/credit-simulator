'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
import { useI18n } from '@/lib/i18n'
import { API_BASE } from '@/lib/constants'
import { LocaleToggle } from '@/components/LocaleToggle'
import { DarkModeToggle } from '@/components/DarkModeToggle'

export default function Home() {
  const { t } = useI18n()
  const [user, setUser] = useState<{ email?: string } | null>(null)

  useEffect(() => {
    if (!process.env.NEXT_PUBLIC_SUPABASE_URL || !process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY) return
    const supabase = createClient()
    supabase.auth
      .getUser()
      .then(({ data }) => setUser(data.user ?? null))
      .catch(() => setUser(null))
  }, [])

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <div className="absolute top-4 right-4 flex items-center gap-3">
        <DarkModeToggle />
        <LocaleToggle />
      </div>

      <h1 className="text-4xl font-bold tracking-tight">{t('nav.title')}</h1>
      <p className="text-gray-500 dark:text-gray-400 text-center max-w-md">{t('home.tagline')}</p>

      <div className="flex gap-4">
        <Link
          href="/simulate"
          className="rounded-lg bg-black text-white dark:bg-white dark:text-black px-6 py-3 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900"
        >
          {t('nav.run')}
        </Link>
        {user ? (
          <Link
            href="/history"
            className="rounded-lg border dark:border-gray-700 px-6 py-3 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:focus-visible:ring-gray-600"
          >
            {t('nav.history')}
          </Link>
        ) : (
          <Link
            href="/auth"
            className="rounded-lg border dark:border-gray-700 px-6 py-3 font-medium hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:focus-visible:ring-gray-600"
          >
            {t('nav.signin')}
          </Link>
        )}
      </div>

      {user && (
        <div className="flex gap-4 text-sm text-gray-500 dark:text-gray-400">
          <Link href="/preferences" className="hover:text-gray-800 dark:hover:text-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:focus-visible:ring-gray-600 rounded">
            {t('nav.preferences')}
          </Link>
          <span>·</span>
          <Link href="/settings" className="hover:text-gray-800 dark:hover:text-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:focus-visible:ring-gray-600 rounded">
            {t('nav.settings')}
          </Link>
        </div>
      )}

      <div className="flex gap-4 text-sm text-gray-400 dark:text-gray-500">
        <Link href="/rates" className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:focus-visible:ring-gray-600 rounded">
          {t('nav.rates')}
        </Link>
        {user && (
          <>
            <span>·</span>
            <Link href="/alerts" className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:focus-visible:ring-gray-600 rounded">
              {t('nav.alerts')}
            </Link>
          </>
        )}
      </div>

      <div className="mt-2 text-xs text-gray-300 dark:text-gray-600">
        <a
          href={`${API_BASE}/api/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-gray-500 dark:hover:text-gray-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:focus-visible:ring-gray-600 rounded"
        >
          {t('nav.api_docs')} ↗
        </a>
      </div>
    </main>
  )
}
