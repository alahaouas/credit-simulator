import { useState, useEffect, useCallback } from 'react'
import { TOUR_DONE_KEY } from '@/lib/constants'

const TOTAL_STEPS = 5

export function useTour() {
  const [step, setStep] = useState<number | null>(null)
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (localStorage.getItem(TOUR_DONE_KEY)) {
      setDone(true)
    } else {
      setStep(0)
    }
  }, [])

  const next = useCallback(() => {
    setStep(s => {
      if (s === null) return null
      if (s >= TOTAL_STEPS - 1) {
        localStorage.setItem(TOUR_DONE_KEY, '1')
        setDone(true)
        return null
      }
      return s + 1
    })
  }, [])

  const skip = useCallback(() => {
    localStorage.setItem(TOUR_DONE_KEY, '1')
    setDone(true)
    setStep(null)
  }, [])

  const restart = useCallback(() => {
    localStorage.removeItem(TOUR_DONE_KEY)
    setDone(false)
    setStep(0)
  }, [])

  return { step, totalSteps: TOTAL_STEPS, next, skip, restart, done }
}
