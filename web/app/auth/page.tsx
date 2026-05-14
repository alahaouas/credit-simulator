'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase'
import { useI18n } from '@/lib/i18n'

export default function AuthPage() {
  const { t } = useI18n()
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    const supabase = createClient()
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: { emailRedirectTo: `${location.origin}/auth/callback` },
    })
    if (error) setError(error.message)
    else setSubmitted(true)
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
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-80">
        <h1 className="text-2xl font-semibold">{t('auth.title')}</h1>
        <input
          type="email"
          placeholder={t('auth.email_placeholder')}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="border rounded px-3 py-2"
        />
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button type="submit" className="bg-black text-white rounded px-4 py-2">
          {t('auth.send')}
        </button>
      </form>
    </main>
  )
}
