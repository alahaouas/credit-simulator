import type { Metadata } from 'next'

// The signed-in user’s own simulations. A redirect to sign-in is not a noindex: without
// this, the URL still enters the index, as a soft 404.
export const metadata: Metadata = {
  title: 'My simulations',
  robots: { index: false, follow: false },
  // The root layout's canonical is inherited otherwise, which would point
  // this page at '/' while also telling crawlers not to index it.
  alternates: { canonical: null },
}

// Server layout: a 'use client' page cannot export metadata (Next ignores it
// silently), so the route's metadata lives here.
export default function HistoryLayout({ children }: { children: React.ReactNode }) {
  return children
}
