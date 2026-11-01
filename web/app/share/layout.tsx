import type { Metadata } from 'next'

// Token-addressed share links: readable only by whoever holds the token, and every token
// is a distinct URL for the same page.
export const metadata: Metadata = {
  title: 'Shared simulation',
  robots: { index: false, follow: false },
  // The root layout's canonical is inherited otherwise, which would point
  // this page at '/' while also telling crawlers not to index it.
  alternates: { canonical: null },
}

// Server layout: a 'use client' page cannot export metadata (Next ignores it
// silently), so the route's metadata lives here.
export default function ShareLayout({ children }: { children: React.ReactNode }) {
  return children
}
