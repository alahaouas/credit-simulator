'use client'

import SimulatorForm from '@/components/SimulatorForm'
import { useI18n } from '@/lib/i18n'
import { DarkModeToggle } from '@/components/DarkModeToggle'
import { LocaleToggle } from '@/components/LocaleToggle'

export default function SimulatePage() {
  const { t } = useI18n()
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="absolute top-4 right-4 flex items-center gap-3">
        <DarkModeToggle />
        <LocaleToggle />
      </div>
      <div className="w-full max-w-lg">
        <h1 className="text-3xl font-bold tracking-tight mb-2">{t('simulate.title')}</h1>
        <p className="text-gray-500 dark:text-gray-400 mb-8">{t('simulate.subtitle')}</p>
        <SimulatorForm />
      </div>
    </main>
  )
}
