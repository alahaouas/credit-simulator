'use client'

import { useState } from 'react'
import { createClient } from '@/lib/supabase'
import { generateShareToken, revokeShareToken, ApiError } from '@/lib/api'

interface UseShareTokenOptions {
  genericErrorMessage: string
  onTokenChange?: (id: string, token: string | null) => void
  onError?: (message: string) => void
}

export function useShareToken({ genericErrorMessage, onTokenChange, onError }: UseShareTokenOptions) {
  const [shareTokens, setShareTokens] = useState<Record<string, string | null>>({})
  const [shareLoading, setShareLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  function shareUrl(token: string) {
    return `${window.location.origin}/share/${token}`
  }

  async function generateToken(id: string) {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    setShareLoading(true)
    try {
      const token = await generateShareToken(id, session.access_token)
      setShareTokens(prev => ({ ...prev, [id]: token }))
      onTokenChange?.(id, token)
    } catch (e) {
      onError?.(e instanceof ApiError ? e.message : genericErrorMessage)
    } finally {
      setShareLoading(false)
    }
  }

  async function revokeToken(id: string) {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    setShareLoading(true)
    try {
      await revokeShareToken(id, session.access_token)
      setShareTokens(prev => ({ ...prev, [id]: null }))
      onTokenChange?.(id, null)
    } catch (e) {
      onError?.(e instanceof ApiError ? e.message : genericErrorMessage)
    } finally {
      setShareLoading(false)
    }
  }

  async function copy(token: string) {
    await navigator.clipboard.writeText(shareUrl(token))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return { shareTokens, shareLoading, copied, shareUrl, generateToken, revokeToken, copy }
}
