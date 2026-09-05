'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import {
  listSimulations, deleteSimulation, getSimulation, updateSimulationMeta,
  getSimulationStats,
  ApiError, SimulateRequest, SimulationStats, SavedSimulation,
} from '@/lib/api'
import { DEFAULT_COUNTRY, SESSION_RESULT_KEY, SESSION_CLONE_KEY } from '@/lib/constants'
import { useI18n, type TranslationKey } from '@/lib/i18n'
import { useShareToken } from '@/hooks/useShareToken'
import { LocaleToggle } from '@/components/LocaleToggle'
import { DarkModeToggle } from '@/components/DarkModeToggle'

type SimulationSummary = SavedSimulation

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

function inputSummary(inputs: SimulateRequest, t: (k: TranslationKey) => string) {
  const price = parseFloat(inputs.property_price).toLocaleString(undefined, { maximumFractionDigits: 0 })
  const country = inputs.country ?? DEFAULT_COUNTRY
  const fixedMonths = inputs.fixed_loan_duration_months
  const duration = fixedMonths ? `${fixedMonths / 12}y` : t('history.duration_auto')
  return `${country} · ${price} · ${duration}`
}

function StatsCards({ stats, t }: { stats: SimulationStats; t: (k: TranslationKey) => string }) {
  if (stats.total_count === 0) return null
  const cards = [
    { label: t('stats.total'), value: String(stats.total_count) },
    {
      label: t('stats.avg_monthly'),
      value: stats.avg_monthly_installment
        ? parseFloat(stats.avg_monthly_installment).toLocaleString(undefined, { maximumFractionDigits: 0 })
        : '—',
    },
    {
      label: t('stats.avg_duration'),
      value: stats.avg_loan_duration_months
        ? `${stats.avg_loan_duration_months} ${t('stats.months')}`
        : '—',
    },
    {
      label: t('stats.total_principal'),
      value: stats.total_principal
        ? parseFloat(stats.total_principal).toLocaleString(undefined, { maximumFractionDigits: 0 })
        : '—',
    },
  ]
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
      {cards.map(c => (
        <div key={c.label} className="rounded-lg border dark:border-gray-700 p-4">
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-1">{c.label}</p>
          <p className="text-lg font-semibold">{c.value}</p>
        </div>
      ))}
    </div>
  )
}

export default function HistoryPage() {
  const router = useRouter()
  const { t } = useI18n()
  const [items, setItems] = useState<SimulationSummary[]>([])
  const [stats, setStats] = useState<SimulationStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)
  const [editing, setEditing] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editTags, setEditTags] = useState('')
  const [saving, setSaving] = useState(false)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [sharing, setSharing] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)
  const searchDebounce = useRef<ReturnType<typeof setTimeout> | null>(null)

  const {
    shareTokens, shareLoading, copied, shareUrl,
    generateToken: handleGenerateToken, revokeToken: handleRevokeToken, copy: handleCopy,
  } = useShareToken({
    genericErrorMessage: t('error.generic'),
    onTokenChange: (id, token) => setItems(prev => prev.map(s => s.id === id ? { ...s, share_token: token } : s)),
    onError: setError,
  })

  function toggleSelect(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else if (next.size < 3) {
        next.add(id)
      }
      return next
    })
  }

  const load = useCallback(async (query: string) => {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) { router.replace('/auth'); return }
    try {
      const [page, statsData] = await Promise.all([
        listSimulations(session.access_token, query ? { search: query } : undefined),
        getSimulationStats(session.access_token),
      ])
      setItems(page.items)
      setNextCursor(page.next_cursor)
      setStats(statsData)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    } finally {
      setLoading(false)
    }
  }, [router, t])

  useEffect(() => { load('') }, [load])

  function handleSearchChange(value: string) {
    setSearch(value)
    if (searchDebounce.current) clearTimeout(searchDebounce.current)
    searchDebounce.current = setTimeout(async () => {
      setLoading(true)
      setError(null)
      await load(value)
    }, 400)
  }

  async function handleLoadMore() {
    if (!nextCursor) return
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    setLoadingMore(true)
    try {
      const page = await listSimulations(session.access_token, {
        ...(search ? { search } : {}),
        cursor: nextCursor,
      })
      setItems(prev => [...prev, ...page.items])
      setNextCursor(page.next_cursor)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    } finally {
      setLoadingMore(false)
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm(t('history.confirm_delete') || 'Are you sure you want to delete this simulation?')) return
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    setDeleting(id)
    try {
      await deleteSimulation(id, session.access_token)
      setItems(prev => prev.filter(s => s.id !== id))
      if (stats) setStats(s => s ? { ...s, total_count: s.total_count - 1 } : s)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    } finally {
      setDeleting(null)
    }
  }

  async function handleView(id: string) {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    try {
      const sim = await getSimulation(id, session.access_token)
      sessionStorage.setItem(SESSION_RESULT_KEY, JSON.stringify(sim.result))
      router.push('/results')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    }
  }

  async function handleClone(id: string) {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    try {
      const sim = await getSimulation(id, session.access_token)
      sessionStorage.setItem(SESSION_CLONE_KEY, JSON.stringify(sim.inputs))
      router.push('/simulate')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    }
  }

  function startEdit(sim: SimulationSummary) {
    setEditing(sim.id)
    setEditName(sim.name ?? '')
    setEditTags((sim.tags ?? []).join(', '))
    setError(null)
  }

  function cancelEdit() {
    setEditing(null)
    setEditName('')
    setEditTags('')
  }

  async function saveEdit(id: string) {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    const tags = editTags.split(',').map(s => s.trim()).filter(Boolean)
    setSaving(true)
    try {
      const updated = await updateSimulationMeta(
        id, { name: editName.trim() || null, tags }, session.access_token,
      )
      setItems(prev => prev.map(s =>
        s.id === id ? { ...s, name: updated.name, tags: updated.tags } : s,
      ))
      cancelEdit()
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500 dark:text-gray-400">{t('history.loading')}</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('history.title')}</h1>
        <div className="flex items-center gap-3">
          <DarkModeToggle />
          <LocaleToggle />
          {selected.size >= 2 && (
            <Link
              href={`/compare?ids=${Array.from(selected).join(',')}`}
              className="text-sm rounded-lg px-4 py-2 bg-black text-white dark:bg-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900"
            >
              {t('history.compare')} ({selected.size})
            </Link>
          )}
          <Link href="/simulate" className="text-sm border dark:border-gray-700 rounded-lg px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400 dark:focus-visible:ring-offset-gray-900">
            {t('history.new')}
          </Link>
        </div>
      </div>

      {stats && <StatsCards stats={stats} t={t} />}

      <div className="mb-6">
        <label htmlFor="historySearch" className="sr-only">{t('history.search_placeholder')}</label>
        <input
          id="historySearch"
          type="search"
          value={search}
          onChange={e => handleSearchChange(e.target.value)}
          placeholder={t('history.search_placeholder')}
          className="w-full text-sm border dark:border-gray-700 rounded-lg px-4 py-2 bg-white dark:bg-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-400 dark:focus:ring-gray-600"
        />
      </div>

      {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

      {items.length === 0 && !loading ? (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          {search ? (
            <p className="mb-4">{t('history.no_results')}</p>
          ) : (
            <>
              <p className="mb-4">{t('history.empty')}</p>
              <Link href="/simulate" className="rounded-lg bg-black text-white dark:bg-white dark:text-black px-6 py-3 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900">
                {t('history.first')}
              </Link>
            </>
          )}
        </div>
      ) : (
        <>
        <ul className="divide-y dark:divide-gray-700 border dark:border-gray-700 rounded-lg overflow-hidden">
          {items.map(sim => (
            <li key={sim.id} className="px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800">
              {editing === sim.id ? (
                <div className="flex flex-col gap-2">
                  <label htmlFor={`editName-${sim.id}`} className="sr-only">{t('history.name_placeholder')}</label>
                  <input
                    id={`editName-${sim.id}`}
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    maxLength={120}
                    placeholder={t('history.name_placeholder')}
                    className="w-full text-sm border dark:border-gray-600 rounded px-3 py-1.5 bg-white dark:bg-gray-800 dark:text-gray-100"
                  />
                  <label htmlFor={`editTags-${sim.id}`} className="sr-only">{t('history.tags_placeholder')}</label>
                  <input
                    id={`editTags-${sim.id}`}
                    value={editTags}
                    onChange={e => setEditTags(e.target.value)}
                    placeholder={t('history.tags_placeholder')}
                    className="w-full text-sm border dark:border-gray-600 rounded px-3 py-1.5 bg-white dark:bg-gray-800 dark:text-gray-100"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => saveEdit(sim.id)}
                      disabled={saving}
                      aria-label={saving ? t('aria.loading') : t('history.save')}
                      className="text-sm px-3 py-1.5 rounded bg-black text-white dark:bg-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-40 min-h-[32px] flex items-center justify-center min-w-[60px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900"
                    >
                      {saving ? (
                        <svg aria-hidden="true" className="animate-spin h-4 w-4 text-white dark:text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      ) : (
                        t('history.save')
                      )}
                    </button>
                    <button
                      onClick={cancelEdit}
                      disabled={saving}
                      className="text-sm px-3 py-1.5 rounded border dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                    >
                      {t('history.cancel')}
                    </button>
                  </div>
                </div>
              ) : sharing === sim.id ? (
                <div className="flex flex-col gap-3">
                  <p className="text-xs text-gray-500 dark:text-gray-400">{t('history.share_hint')}</p>
                  {(() => {
                    const token = shareTokens[sim.id] ?? sim.share_token ?? null
                    return token ? (
                      <div className="flex flex-col gap-2">
                        <div className="flex gap-2 items-center">
                          <label htmlFor={`shareUrl-${sim.id}`} className="sr-only">{t('history.share_url_label')}</label>
                          <input
                            id={`shareUrl-${sim.id}`}
                            readOnly
                            value={shareUrl(token)}
                            className="flex-1 text-xs border dark:border-gray-600 rounded px-3 py-1.5 bg-gray-50 dark:bg-gray-900 dark:text-gray-300 truncate"
                          />
                          <button
                            onClick={() => handleCopy(token)}
                            aria-live="polite"
                            className="text-sm px-3 py-1.5 rounded border dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                          >
                            {/* Both labels share one grid cell, so the button keeps the width of
                                the longest one in every locale and never shifts on toggle. */}
                            <span className="grid place-items-center">
                              <span aria-hidden="true" className="col-start-1 row-start-1 invisible whitespace-nowrap">{t('history.share_copy')}</span>
                              <span aria-hidden="true" className="col-start-1 row-start-1 invisible whitespace-nowrap">{t('history.share_copied')}</span>
                              <span className="col-start-1 row-start-1 whitespace-nowrap">
                                {copied ? t('history.share_copied') : t('history.share_copy')}
                              </span>
                            </span>
                          </button>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              if (window.confirm(t('history.confirm_revoke') || 'Are you sure you want to revoke this share token?')) {
                                handleRevokeToken(sim.id)
                              }
                            }}
                            disabled={shareLoading}
                            aria-label={shareLoading ? t('aria.loading') : t('history.share_revoke')}
                            className="text-sm px-3 py-1.5 rounded border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40 min-h-[32px] min-w-[100px] flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                          >
                            {shareLoading ? (
                              <svg aria-hidden="true" className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                            ) : (
                              t('history.share_revoke')
                            )}
                          </button>
                          <button
                            onClick={() => setSharing(null)}
                            className="text-sm px-3 py-1.5 rounded border dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                          >
                            {t('history.cancel')}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleGenerateToken(sim.id)}
                          disabled={shareLoading}
                          aria-label={shareLoading ? t('aria.loading') : t('history.share_generate')}
                          className="text-sm px-3 py-1.5 rounded bg-black text-white dark:bg-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-black dark:focus-visible:ring-white dark:focus-visible:ring-offset-gray-900 min-h-[32px] min-w-[110px] flex items-center justify-center"
                        >
                          {shareLoading ? (
                            <svg aria-hidden="true" className="animate-spin h-4 w-4 text-white dark:text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                          ) : (
                            t('history.share_generate')
                          )}
                        </button>
                        <button
                          onClick={() => setSharing(null)}
                          className="text-sm px-3 py-1.5 rounded border dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                        >
                          {t('history.cancel')}
                        </button>
                      </div>
                    )
                  })()}
                </div>
              ) : (
                <div className="flex items-center justify-between gap-4">
                  <label htmlFor={`compare-${sim.id}`} className="sr-only">
                    {t('history.compare')}
                  </label>
                  <input
                    id={`compare-${sim.id}`}
                    type="checkbox"
                    checked={selected.has(sim.id)}
                    onChange={() => toggleSelect(sim.id)}
                    disabled={!selected.has(sim.id) && selected.size >= 3}
                    className="shrink-0 h-4 w-4 rounded border-gray-300 dark:border-gray-600 accent-black dark:accent-white disabled:opacity-40 cursor-pointer disabled:cursor-default"
                  />
                  <div className="min-w-0 flex-1">
                    {sim.name ? (
                      <>
                        <p className="font-medium truncate">{sim.name}</p>
                        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 truncate">{inputSummary(sim.inputs, t)}</p>
                      </>
                    ) : (
                      <p className="font-medium truncate">{inputSummary(sim.inputs, t)}</p>
                    )}
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{formatDate(sim.created_at)}</p>
                    {sim.tags && sim.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {sim.tags.map(tag => (
                          <span key={tag} className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded px-2 py-0.5">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => startEdit(sim)}
                      className="text-sm px-3 py-1.5 rounded border dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                    >
                      {t('history.edit')}
                    </button>
                    <button
                      onClick={() => handleClone(sim.id)}
                      className="text-sm px-3 py-1.5 rounded border dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                    >
                      {t('history.clone')}
                    </button>
                    <button
                      onClick={() => { setSharing(sim.id); setError(null) }}
                      className="text-sm px-3 py-1.5 rounded border dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                    >
                      {t('history.share')}
                    </button>
                    <button
                      onClick={() => handleView(sim.id)}
                      className="text-sm px-3 py-1.5 rounded border dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400"
                    >
                      {t('history.view')}
                    </button>
                    <button
                      onClick={() => handleDelete(sim.id)}
                      disabled={deleting === sim.id}
                      aria-label={deleting === sim.id ? t('aria.loading') : t('history.delete')}
                      className="text-sm px-3 py-1.5 rounded border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40 min-h-[32px] flex items-center justify-center min-w-[70px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                    >
                      {deleting === sim.id ? (
                        <svg aria-hidden="true" className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      ) : (
                        t('history.delete')
                      )}
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
        {items.length >= 2 && selected.size === 0 && (
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-3 text-center">{t('history.compare_hint')}</p>
        )}
        {nextCursor && (
          <div className="mt-4 text-center">
            <button
              onClick={handleLoadMore}
              disabled={loadingMore}
              aria-label={loadingMore ? t('aria.loading') : t('history.load_more')}
              className="text-sm border dark:border-gray-700 rounded-lg px-6 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-40 min-h-[38px] inline-flex items-center justify-center min-w-[120px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400 dark:focus-visible:ring-offset-gray-900"
            >
              {loadingMore ? (
                <svg aria-hidden="true" className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                t('history.load_more')
              )}
            </button>
          </div>
        )}
        </>
      )}

      <div className="mt-6 text-center">
        <Link href="/" className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 dark:focus-visible:ring-gray-600 rounded">{t('nav.home')}</Link>
      </div>
    </main>
  )
}
