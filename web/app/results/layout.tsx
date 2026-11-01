import type { Metadata } from 'next'

// Renders one simulation from session state. Indexed, it would produce unbounded near-
// duplicate URLs for the same page.
export const metadata: Metadata = {
  title: 'Simulation results',
  robots: { index: false, follow: false },
  // The root layout's canonical is inherited otherwise, which would point
  // this page at '/' while also telling crawlers not to index it.
  alternates: { canonical: null },
}

// Server layout: a 'use client' page cannot export metadata (Next ignores it
// silently), so the route's metadata lives here.
export default function ResultsLayout({ children }: { children: React.ReactNode }) {
  return children
}
