'use client'

import { useState, useId } from 'react'
import { OptimizedResult } from '@/lib/api'
import { useI18n } from '@/lib/i18n'

interface Props {
  result: OptimizedResult
  currency: string
}

interface TaxComponent {
  nameEn: string
  nameFr: string
  rate: number
}

// Indicative purchase-cost components per country.
// Rates are fractions of the property price and are designed to sum to the
// purchase_tax_rate embedded in the country profile.
const TAX_BREAKDOWN: Record<string, TaxComponent[]> = {
  BE: [
    { nameEn: 'Registration tax', nameFr: "Droits d'enregistrement", rate: 0.100 },
    { nameEn: 'Notary fees', nameFr: 'Honoraires du notaire', rate: 0.010 },
    { nameEn: 'Mortgage registration', nameFr: 'Inscription hypothécaire', rate: 0.010 },
    { nameEn: 'Admin & misc.', nameFr: 'Frais administratifs', rate: 0.005 },
  ],
  FR: [
    { nameEn: 'Transfer tax (droits de mutation)', nameFr: 'Droits de mutation', rate: 0.058 },
    { nameEn: 'Land registration', nameFr: 'Taxe de publicité foncière', rate: 0.010 },
    { nameEn: 'Notary fees', nameFr: 'Honoraires du notaire', rate: 0.008 },
    { nameEn: 'Admin & disbursements', nameFr: 'Frais et débours', rate: 0.009 },
  ],
  DE: [
    { nameEn: 'Real estate transfer tax (Grunderwerbsteuer)', nameFr: 'Taxe de transfert immobilier', rate: 0.035 },
    { nameEn: 'Notary fees', nameFr: 'Honoraires du notaire', rate: 0.010 },
    { nameEn: 'Land registry fee', nameFr: 'Frais de cadastre', rate: 0.005 },
  ],
  ES: [
    { nameEn: 'Transfer tax (ITP)', nameFr: 'Taxe de transfert (ITP)', rate: 0.060 },
    { nameEn: 'Stamp duty (AJD)', nameFr: 'Actes juridiques documentés', rate: 0.010 },
    { nameEn: 'Notary fees', nameFr: 'Honoraires du notaire', rate: 0.005 },
    { nameEn: 'Land registry fee', nameFr: 'Frais de registre foncier', rate: 0.005 },
  ],
  PT: [
    { nameEn: 'Property transfer tax (IMT)', nameFr: 'Taxe de transfert (IMT)', rate: 0.055 },
    { nameEn: 'Stamp duty', nameFr: 'Timbre fiscal', rate: 0.008 },
    { nameEn: 'Notary & registry fees', nameFr: 'Frais notariaux et registre', rate: 0.007 },
  ],
  IT: [
    { nameEn: 'Registration tax', nameFr: "Taxe d'enregistrement", rate: 0.020 },
    { nameEn: 'Land register tax', nameFr: 'Taxe cadastrale', rate: 0.010 },
    { nameEn: 'Mortgage tax', nameFr: 'Taxe hypothécaire', rate: 0.005 },
    { nameEn: 'Notary fees', nameFr: 'Honoraires du notaire', rate: 0.005 },
  ],
  GB: [
    { nameEn: 'Stamp Duty Land Tax (SDLT)', nameFr: 'Droits de timbre (SDLT)', rate: 0.020 },
    { nameEn: 'Land registry fee', nameFr: 'Frais de registre foncier', rate: 0.005 },
    { nameEn: 'Legal & conveyancing fees', nameFr: 'Frais juridiques', rate: 0.005 },
  ],
  US: [
    { nameEn: 'Transfer tax', nameFr: 'Taxe de transfert', rate: 0.005 },
    { nameEn: 'Title insurance', nameFr: 'Assurance titre', rate: 0.005 },
    { nameEn: 'Recording fees', nameFr: "Frais d'enregistrement", rate: 0.003 },
    { nameEn: 'Legal fees', nameFr: 'Frais juridiques', rate: 0.003 },
    { nameEn: 'Other closing costs', nameFr: 'Autres frais de clôture', rate: 0.009 },
  ],
}

function fmt(val: number, currency: string) {
  return `${currency}${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtPct(rate: number) {
  return `${(rate * 100).toFixed(2)}%`
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border dark:border-gray-700 p-3 flex flex-col gap-1">
      <span className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">{label}</span>
      <span className="text-base font-semibold">{value}</span>
    </div>
  )
}

export default function PurchaseTaxPanel({ result, currency }: Props) {
  const { t, locale } = useI18n()
  const [showTable, setShowTable] = useState(false)
  const contentId = useId()

  const country = result.country?.toUpperCase() ?? ''
  const propertyPrice = parseFloat(result.property_price)
  const components = TAX_BREAKDOWN[country]

  if (!components || isNaN(propertyPrice)) return null

  const rows = components.map(c => ({
    name: locale === 'fr' ? c.nameFr : c.nameEn,
    rate: c.rate,
    amount: propertyPrice * c.rate,
  }))

  const totalRate = rows.reduce((s, r) => s + r.rate, 0)
  const totalAmount = rows.reduce((s, r) => s + r.amount, 0)

  return (
    <section className="mb-8 border dark:border-gray-700 rounded-xl p-5">
      <h2 className="text-lg font-semibold mb-1">{t('tax.title')}</h2>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{t('tax.subtitle')}</p>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
        <Stat label={t('tax.property_price')} value={fmt(propertyPrice, currency)} />
        <Stat label={t('tax.total_rate')} value={fmtPct(totalRate)} />
        <Stat label={t('tax.total_amount')} value={fmt(totalAmount, currency)} />
      </div>

      <button
        onClick={() => setShowTable(s => !s)}
        aria-expanded={showTable}
        aria-controls={contentId}
        className="text-sm text-gray-500 dark:text-gray-400 underline mb-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded"
      >
        {showTable ? t('tax.hide_table') : t('tax.show_table')}
      </button>

      {showTable && (
        <div id={contentId}>
          <div className="overflow-x-auto rounded-lg border dark:border-gray-700 text-xs mb-3">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-500 dark:text-gray-400">{t('tax.col_component')}</th>
                  <th className="px-3 py-2 text-right font-medium text-gray-500 dark:text-gray-400">{t('tax.col_rate')}</th>
                  <th className="px-3 py-2 text-right font-medium text-gray-500 dark:text-gray-400">{t('tax.col_amount')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                {rows.map((row, i) => (
                  <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-3 py-1.5">{row.name}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{fmtPct(row.rate)}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">{fmt(row.amount, currency)}</td>
                  </tr>
                ))}
                <tr className="bg-gray-50 dark:bg-gray-800 font-semibold">
                  <td className="px-3 py-1.5">{t('tax.total')}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{fmtPct(totalRate)}</td>
                  <td className="px-3 py-1.5 text-right tabular-nums">{fmt(totalAmount, currency)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 italic">{t('tax.note')}</p>
        </div>
      )}
    </section>
  )
}
