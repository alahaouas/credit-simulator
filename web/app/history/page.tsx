'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import {
  listSimulations, deleteSimulation, getSimulation,
  getSimulationStats, ApiError, SimulateRequest, SimulationStats,
} from '@/lib/api'
import { DEFAULT_COUNTRY, SESSION_RESULT_KEY } from '@/lib/constants'
import { useI18n, type TranslationKey } from '@/lib/i18n'
import { LocaleToggle } from '@/components/LocaleToggle'
import { DarkModeToggle } from '@/components/DarkModeToggle'

type SimulationSummary = {
  id: string
  created_at: string
  inputs: SimulateRequest
}

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

  const load = useCallback(async () => {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) { router.replace('/auth'); return }
    try {
      const [simulations, statsData] = await Promise.all([
        listSimulations(session.access_token),
        getSimulationStats(session.access_token),
      ])
      setItems(simulations)
      setStats(statsData)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('error.generic'))
    } finally {
      setLoading(false)
    }
  }, [router, t])

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string) {
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
          <Link href="/simulate" className="text-sm border dark:border-gray-700 rounded-lg px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
            {t('history.new')}
          </Link>
        </div>
      </div>

      {stats && <StatsCards stats={stats} t={t} />}

      {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

      {items.length === 0 ? (
        <div className="text-center py-16 text-gray-400 dark:text-gray-500">
          <p className="mb-4">{t('history.empty')}</p>
          <Link href="/simulate" className="rounded-lg bg-black text-white dark:bg-white dark:text-black px-6 py-3 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors">
            {t('history.first')}
          </Link>
        </div>
      ) : (
        <ul className="divide-y dark:divide-gray-700 border dark:border-gray-700 rounded-lg overflow-hidden">
          {items.map(sim => (
            <li key={sim.id} className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800">
              <div className="min-w-0">
                <p className="font-medium truncate">{inputSummary(sim.inputs, t)}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{formatDate(sim.created_at)}</p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => handleView(sim.id)}
                  className="text-sm px-3 py-1.5 rounded border dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  {t('history.view')}
                </button>
                <button
                  onClick={() => handleDelete(sim.id)}
                  disabled={deleting === sim.id}
                  className="text-sm px-3 py-1.5 rounded border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-40"
                >
                  {deleting === sim.id ? '…' : t('history.delete')}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-6 text-center">
        <Link href="/" className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">{t('nav.home')}</Link>
      </div>
    </main>
  )
}
