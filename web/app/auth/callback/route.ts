import { createServerSupabaseClient } from '@/lib/supabase-server'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')

  if (code) {
    const supabase = await createServerSupabaseClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      return NextResponse.redirect(`${origin}/`)
    }
  }

  // Missing or invalid/expired code — send the user back to sign-in with an
  // error flag instead of silently landing on the home page logged out.
  return NextResponse.redirect(`${origin}/auth?error=callback_failed`)
}
