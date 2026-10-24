'use client'

import Link from 'next/link'
import { useI18n, type TranslationKey } from '@/lib/i18n'
import { company } from '@/lib/company'

export default function LegalPage() {
  const { t } = useI18n()

  const rows: [TranslationKey, string][] = [
    ['legal.publisher', company.name],
    ['legal.address', company.address],
    ['legal.email', company.email],
    ['legal.bce', company.bceNumber],
    ['legal.vat', company.vatNumber],
    ['legal.court', company.court],
  ]

  return (
    <main className="mx-auto max-w-2xl p-8 space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">{t('legal.title')}</h1>
      <p className="text-gray-500 dark:text-gray-400">{t('legal.intro')}</p>
      <dl className="divide-y divide-gray-200 dark:divide-gray-700 border-y border-gray-200 dark:border-gray-700">
        {rows.map(([key, value]) => (
          <div key={key} className="grid gap-1 py-3 sm:grid-cols-3 sm:gap-4">
            <dt className="font-semibold">{t(key)}</dt>
            <dd className="sm:col-span-2">
              {value || <span className="text-gray-500 dark:text-gray-400">{t('legal.missing')}</span>}
            </dd>
          </div>
        ))}
      </dl>
      <p className="text-gray-500 dark:text-gray-400">
        © {new Date().getFullYear()} {company.name}. {t('legal.rights')}
      </p>
      <Link href="/" className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded">{t('nav.home')}</Link>
    </main>
  )
}
