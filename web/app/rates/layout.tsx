import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Mortgage rates and lending limits by country',
  description:
    'Reference mortgage rates, insurance rates, purchase taxes, minimum down payment, maximum debt ratio and maximum term for Belgium, France, Germany, Spain, Italy, Portugal, the UK and the US.',
  alternates: { canonical: '/rates' },
}

// Server layout: a 'use client' page cannot export metadata (Next ignores it
// silently), so the route's metadata lives here and the page stays a client
// component.
export default function RatesLayout({ children }: { children: React.ReactNode }) {
  return children
}
