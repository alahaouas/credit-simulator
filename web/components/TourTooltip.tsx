'use client'

import type { ReactNode } from 'react'

interface TourTooltipProps {
  active: boolean
  step: number
  total: number
  title: string
  description: string
  nextLabel: string
  skipLabel: string
  onNext: () => void
  onSkip: () => void
  children: ReactNode
}

export default function TourTooltip({
  active,
  step,
  total,
  title,
  description,
  nextLabel,
  skipLabel,
  onNext,
  onSkip,
  children,
}: TourTooltipProps) {
  return (
    <div className={`relative${active ? ' ring-2 ring-blue-500 ring-offset-2 rounded-md' : ''}`}>
      {children}
      {active && (
        <div
          role="dialog"
          aria-label={title}
          className="absolute left-0 top-full mt-2 z-50 w-72 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-600 rounded-lg shadow-xl p-3"
        >
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {step + 1} / {total}
            </span>
            <button
              type="button"
              onClick={onSkip}
              className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded"
            >
              {skipLabel}
            </button>
          </div>
          <p className="text-sm font-semibold mb-1 dark:text-gray-100">{title}</p>
          <p className="text-xs text-gray-600 dark:text-gray-300 mb-3">{description}</p>
          <div className="flex justify-end">
            <button
              type="button"
              onClick={onNext}
              className="text-xs bg-black dark:bg-white text-white dark:text-black rounded px-3 py-1 font-medium hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900"
            >
              {nextLabel}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
