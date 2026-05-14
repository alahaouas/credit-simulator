import Link from 'next/link'
import { createServerSupabaseClient } from '@/lib/supabase-server'

export default async function Home() {
  const supabase = await createServerSupabaseClient()
  const { data: { user } } = await supabase.auth.getUser()

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-4xl font-bold tracking-tight">Credit Simulator</h1>
      <p className="text-gray-500 text-center max-w-md">
        Find the optimal mortgage plan for your property purchase — down-payment
        analysis, amortization schedule, and sweet-spot breakdown.
      </p>
      <div className="flex gap-4">
        <Link
          href="/simulate"
          className="rounded-lg bg-black text-white px-6 py-3 font-medium hover:bg-gray-800 transition-colors"
        >
          Run simulation
        </Link>
        {user ? (
          <Link
            href="/history"
            className="rounded-lg border px-6 py-3 font-medium hover:bg-gray-50 transition-colors"
          >
            My simulations
          </Link>
        ) : (
          <Link
            href="/auth"
            className="rounded-lg border px-6 py-3 font-medium hover:bg-gray-50 transition-colors"
          >
            Sign in to save results
          </Link>
        )}
      </div>
    </main>
  )
}
