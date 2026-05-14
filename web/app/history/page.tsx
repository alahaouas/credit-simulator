'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase'
import { listSimulations, deleteSimulation, getSimulation, ApiError, SimulateRequest } from '@/lib/api'

type SimulationSummary = {
  id: string
  created_at: string
  inputs: SimulateRequest
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function inputSummary(inputs: SimulateRequest) {
  const price = parseFloat(inputs.property_price).toLocaleString('en-US', { maximumFractionDigits: 0 })
  const country = inputs.country ?? 'BE'
  const duration = inputs.loan_duration_months ? `${inputs.loan_duration_months / 12}y` : 'auto'
  return `${country} · ${price} · ${duration}`
}

export default function HistoryPage() {
  const router = useRouter()
  const [items, setItems] = useState<SimulationSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = useCallback(async () => {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      router.replace('/auth')
      return
    }
    try {
      const simulations = await listSimulations(session.access_token)
      setItems(simulations)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to load simulations.')
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string) {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    setDeleting(id)
    try {
      await deleteSimulation(id, session.access_token)
      setItems(prev => prev.filter(s => s.id !== id))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Delete failed.')
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
      sessionStorage.setItem('simulator_result', JSON.stringify(sim.result))
      router.push('/results')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to load simulation.')
    }
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading…</p>
      </main>
    )
  }

  return (
    <main className="min-h-screen p-8 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight">My simulations</h1>
        <Link href="/simulate" className="text-sm border rounded-lg px-4 py-2 hover:bg-gray-50 transition-colors">
          New simulation
        </Link>
      </div>

      {error && (
        <p className="text-red-500 text-sm mb-4">{error}</p>
      )}

      {items.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="mb-4">No saved simulations yet.</p>
          <Link href="/simulate" className="rounded-lg bg-black text-white px-6 py-3 font-medium hover:bg-gray-800 transition-colors">
            Run your first simulation
          </Link>
        </div>
      ) : (
        <ul className="divide-y border rounded-lg overflow-hidden">
          {items.map(sim => (
            <li key={sim.id} className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-gray-50">
              <div className="min-w-0">
                <p className="font-medium truncate">{inputSummary(sim.inputs)}</p>
                <p className="text-xs text-gray-400 mt-0.5">{formatDate(sim.created_at)}</p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button
                  onClick={() => handleView(sim.id)}
                  className="text-sm px-3 py-1.5 rounded border hover:bg-gray-100 transition-colors"
                >
                  View
                </button>
                <button
                  onClick={() => handleDelete(sim.id)}
                  disabled={deleting === sim.id}
                  className="text-sm px-3 py-1.5 rounded border border-red-200 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-40"
                >
                  {deleting === sim.id ? '…' : 'Delete'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-6 text-center">
        <Link href="/" className="text-sm text-gray-400 hover:text-gray-600">← Home</Link>
      </div>
    </main>
  )
}
