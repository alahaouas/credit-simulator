'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase'
import { useI18n } from '@/lib/i18n'
import { DarkModeToggle } from '@/components/DarkModeToggle'

export default function AuthPage() {
  const { t } = useI18n()
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const supabase = createClient()
    try {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: `${location.origin}/auth/callback` },
      })
      if (error) setError(error.message)
      else setSubmitted(true)
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-lg">{t('auth.check_inbox')}</p>
      </main>
    )
  }

  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="absolute top-4 right-4">
        <DarkModeToggle />
      </div>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-80">
        <h1 className="text-2xl font-semibold">{t('auth.title')}</h1>
        <div className="flex flex-col gap-1">
          <label htmlFor="email" className="sr-only">Email</label>
          <input
            id="email"
            type="email"
            placeholder={t('auth.email_placeholder')}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="border dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-gray-400"
          />
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="bg-black text-white dark:bg-white dark:text-black rounded px-4 py-2 hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-50"
        >
          {loading ? '...' : t('auth.send')}
        </button>
      </form>
    </main>
  )
}
