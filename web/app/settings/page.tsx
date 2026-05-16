'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import { listApiKeys, createApiKey, deleteApiKey, ApiError, ApiKey, CreatedApiKey } from '@/lib/api'
import { useI18n } from '@/lib/i18n'
import { LocaleToggle } from '@/components/LocaleToggle'
import { DarkModeToggle } from '@/components/DarkModeToggle'

function formatDate(iso: string | null) {
  if (!iso) return null
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: 'medium' })
}

export default function SettingsPage() {
  const router = useRouter()
  const { t } = useI18n()
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKey, setNewKey] = useState<CreatedApiKey | null>(null)
  const [copied, setCopied] = useState(false)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) { router.replace('/auth'); return }
    try {
      setKeys(await listApiKeys(session.access_token))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    } finally {
      setLoading(false)
    }
  }, [router, t])

  useEffect(() => { load() }, [load])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    const name = newKeyName.trim()
    if (!name) return
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    setCreating(true)
    setError(null)
    try {
      const created = await createApiKey(name, session.access_token)
      setNewKey(created)
      setKeys(prev => [created, ...prev])
      setNewKeyName('')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(id: string) {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    setDeleting(id)
    try {
      await deleteApiKey(id, session.access_token)
      setKeys(prev => prev.filter(k => k.id !== id))
      if (newKey?.id === id) setNewKey(null)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    } finally {
      setDeleting(null)
    }
  }

  function handleCopy() {
    if (!newKey) return
    navigator.clipboard.writeText(newKey.key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">{t('history.loading')}</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen p-8 max-w-2xl mx-auto">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-3xl font-bold tracking-tight">{t('settings.title')}</h1>
        <div className="flex items-center gap-3">
          <DarkModeToggle />
          <LocaleToggle />
        </div>
      </div>
      <p className="text-gray-500 dark:text-gray-400 text-sm mb-8">{t('settings.desc')}</p>

      {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

      {/* New key banner */}
      {newKey && (
        <div className="mb-6 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-4">
          <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-2">{t('settings.key_warning')}</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 truncate rounded bg-white dark:bg-gray-800 border dark:border-gray-600 px-3 py-1.5 text-xs font-mono">
              {newKey.key}
            </code>
            <button
              onClick={handleCopy}
              className="shrink-0 rounded border dark:border-gray-600 px-3 py-1.5 text-xs hover:bg-white dark:hover:bg-gray-700 transition-colors"
            >
              {copied ? t('settings.copied') : t('settings.copy')}
            </button>
          </div>
        </div>
      )}

      {/* Create form */}
      <form onSubmit={handleCreate} className="flex gap-2 mb-8">
        <input
          type="text"
          value={newKeyName}
          onChange={e => setNewKeyName(e.target.value)}
          placeholder={t('settings.name_placeholder')}
          className="flex-1 rounded-lg border dark:border-gray-600 px-3 py-2 text-sm bg-white dark:bg-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-gray-400"
        />
        <button
          type="submit"
          disabled={creating || !newKeyName.trim()}
          className="rounded-lg bg-black text-white dark:bg-white dark:text-black px-4 py-2 text-sm font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-50"
        >
          {creating ? '…' : t('settings.generate')}
        </button>
      </form>

      {/* Key list */}
      {keys.length === 0 ? (
        <p className="text-center text-gray-400 dark:text-gray-500 py-8">{t('settings.no_keys')}</p>
      ) : (
        <ul className="divide-y dark:divide-gray-700 border dark:border-gray-700 rounded-lg overflow-hidden">
          {keys.map(k => (
            <li key={k.id} className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800">
              <div className="min-w-0">
                <p className="font-medium text-sm">{k.name}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 font-mono mt-0.5">{k.key_prefix}…</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                  {t('settings.created')}: {formatDate(k.created_at)} ·{' '}
                  {t('settings.last_used')}: {k.last_used_at ? formatDate(k.last_used_at) : t('settings.never')}
                </p>
              </div>
              <button
                onClick={() => handleDelete(k.id)}
                disabled={deleting === k.id}
                className="shrink-0 text-sm px-3 py-1.5 rounded border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40"
              >
                {deleting === k.id ? '…' : t('settings.revoke')}
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-8 text-center">
        <Link href="/" className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">{t('nav.home')}</Link>
      </div>
    </main>
  )
}
