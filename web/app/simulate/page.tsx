'use client'

import SimulatorForm from '@/components/SimulatorForm'
import { useI18n } from '@/lib/i18n'

export default function SimulatePage() {
  const { t } = useI18n()
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-lg">
        <h1 className="text-3xl font-bold tracking-tight mb-2">{t('simulate.title')}</h1>
        <p className="text-gray-500 mb-8">{t('simulate.subtitle')}</p>
        <SimulatorForm />
      </div>
    </main>
  )
}
