import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Simulate a mortgage',
  description:
    'Enter the property price, your income and your savings: the simulator finds the optimal loan plan, the monthly payment and the full amortization schedule.',
  alternates: { canonical: '/simulate' },
}

// Server layout: a 'use client' page cannot export metadata (Next ignores it
// silently), so the route's metadata lives here and the page stays a client
// component.
export default function SimulateLayout({ children }: { children: React.ReactNode }) {
  return children
}
