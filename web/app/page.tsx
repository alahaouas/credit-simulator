'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase'
import { useI18n } from '@/lib/i18n'
import { LocaleToggle } from '@/components/LocaleToggle'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export default function Home() {
  const { t } = useI18n()
  const [user, setUser] = useState<{ email?: string } | null>(null)

  useEffect(() => {
    const supabase = createClient()
    supabase.auth.getUser().then(({ data }) => setUser(data.user ?? null))
  }, [])

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <div className="absolute top-4 right-4">
        <LocaleToggle />
      </div>

      <h1 className="text-4xl font-bold tracking-tight">{t('nav.title')}</h1>
      <p className="text-gray-500 text-center max-w-md">{t('home.tagline')}</p>

      <div className="flex gap-4">
        <Link
          href="/simulate"
          className="rounded-lg bg-black text-white px-6 py-3 font-medium hover:bg-gray-800 transition-colors"
        >
          {t('nav.run')}
        </Link>
        {user ? (
          <Link
            href="/history"
            className="rounded-lg border px-6 py-3 font-medium hover:bg-gray-50 transition-colors"
          >
            {t('nav.history')}
          </Link>
        ) : (
          <Link
            href="/auth"
            className="rounded-lg border px-6 py-3 font-medium hover:bg-gray-50 transition-colors"
          >
            {t('nav.signin')}
          </Link>
        )}
      </div>

      {user && (
        <div className="flex gap-4 text-sm text-gray-500">
          <Link href="/preferences" className="hover:text-gray-800 transition-colors">
            {t('nav.preferences')}
          </Link>
          <span>·</span>
          <Link href="/settings" className="hover:text-gray-800 transition-colors">
            {t('nav.settings')}
          </Link>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-300">
        <a
          href={`${API_BASE}/api/docs`}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-gray-500 transition-colors"
        >
          {t('nav.api_docs')} ↗
        </a>
      </div>
    </main>
  )
}
