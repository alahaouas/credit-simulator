import { createBrowserClient } from '@supabase/ssr'
import { isAuthRetryableFetchError } from '@supabase/supabase-js'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}

// A slow/stalled Supabase Auth response (e.g. a cold project) can leave a
// GoTrue call pending forever, so a caller awaiting it never settles. Race
// it against a timeout so the UI can always fall back to an error state.
const AUTH_TIMEOUT_MS = 15000

export function withAuthTimeout<T>(promise: Promise<T>, ms = AUTH_TIMEOUT_MS): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('auth timeout')), ms)
    promise.then(
      (value) => { clearTimeout(timer); resolve(value) },
      (err) => { clearTimeout(timer); reject(err) }
    )
  })
}

// A stalled first attempt is more often a transient client-side blip (cold
// DNS/TLS, a flaky connection) than a genuinely unreachable backend — retry
// once before giving up, so the caller's timeout handling only fires for a
// request that fails twice in a row.
//
// auth-js never rejects signInWithOtp for a network-level failure — it
// catches it internally and resolves with { error: AuthRetryableFetchError }
// instead. Retrying only on a thrown/rejected promise (i.e. only on our own
// withAuthTimeout firing after a genuine >15s hang) misses that far more
// common case entirely, so the resolved result must be checked too.
export async function signInWithMagicLink(email: string, emailRedirectTo: string) {
  const supabase = createClient()
  const attempt = () =>
    withAuthTimeout(supabase.auth.signInWithOtp({ email, options: { emailRedirectTo } }))
  try {
    const result = await attempt()
    if (!result.error || !isAuthRetryableFetchError(result.error)) return result
  } catch {
    // first attempt hung past the timeout — fall through to the retry below
  }
  const retryResult = await attempt()
  // Still a retryable error after the retry — throw so the caller's existing
  // timeout catch handles it too, instead of leaking the raw fetch error text.
  if (retryResult.error && isAuthRetryableFetchError(retryResult.error)) throw retryResult.error
  return retryResult
}
