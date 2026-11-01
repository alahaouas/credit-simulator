import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Legal notice',
  description:
    'Publisher, registered address, company and VAT numbers, and the terms under which the Credit Simulator results are provided.',
  alternates: { canonical: '/legal' },
}

// Server layout: a 'use client' page cannot export metadata (Next ignores it
// silently), so the route's metadata lives here and the page stays a client
// component.
export default function LegalLayout({ children }: { children: React.ReactNode }) {
  return children
}
