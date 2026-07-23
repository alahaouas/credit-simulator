'use client'

import { useState } from 'react'
import {
  OptimizedResult,
  HeatmapCell,
  HeatmapResponse,
  SimulateRequest,
  simulateHeatmap,
  ApiError,
} from '@/lib/api'
import { SESSION_HEATMAP_KEY } from '@/lib/constants'
import { useI18n } from '@/lib/i18n'

interface Props {
  result: OptimizedResult
  inputs: SimulateRequest
  currency: string
}

type Metric = 'total_cost' | 'monthly_installment'

function cellColor(value: number, min: number, max: number): string {
  if (max === min) return 'hsl(120, 65%, 42%)'
  const normalized = (value - min) / (max - min)
  const hue = Math.round(120 - normalized * 120) // green → yellow → red
  return `hsl(${hue}, 65%, 42%)`
}

function fmt(val: string, currency: string) {
  return `${currency}${parseFloat(val).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
}

function buildGrid(cells: HeatmapCell[]) {
  const dps = [...new Set(cells.map(c => c.down_payment))].sort(
    (a, b) => parseFloat(a) - parseFloat(b)
  )
  const durs = [...new Set(cells.map(c => c.duration_months))].sort((a, b) => a - b)
  const index = new Map(cells.map(c => [`${c.down_payment}:${c.duration_months}`, c]))
  return { dps, durs, index }
}

function loadCached(): HeatmapResponse | null {
  if (typeof window === 'undefined') return null
  const raw = sessionStorage.getItem(SESSION_HEATMAP_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export default function SweetSpotHeatmap({ result, inputs, currency }: Props) {
  const { t } = useI18n()
  const [data, setData] = useState<HeatmapResponse | null>(loadCached)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [metric, setMetric] = useState<Metric>('total_cost')
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null)

  async function handleLoad() {
    setLoading(true)
    setError(null)
    try {
      const resp = await simulateHeatmap(inputs)
      setData(resp)
      sessionStorage.setItem(SESSION_HEATMAP_KEY, JSON.stringify(resp))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  const optimalDp = result.down_payment
  const optimalDur = result.loan_duration_months

  if (!data) {
    return (
      <section className="mb-8 border dark:border-gray-700 rounded-xl p-5">
        <h2 className="text-lg font-semibold mb-1">{t('heatmap.title')}</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{t('heatmap.subtitle')}</p>
        {error && <p className="text-sm text-red-600 dark:text-red-400 mb-3">{error}</p>}
        <button
          onClick={handleLoad}
          disabled={loading}
          aria-label={loading ? t('heatmap.loading') : t('heatmap.load')}
          className="flex items-center justify-center min-h-[40px] px-5 py-2 text-sm rounded-lg bg-black text-white dark:bg-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400"
        >
          {loading ? (
            <svg aria-hidden="true" className="animate-spin h-5 w-5 text-white dark:text-black" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : (
            t('heatmap.load')
          )}
        </button>
      </section>
    )
  }

  const { dps, durs, index } = buildGrid(data.cells)

  const feasibleValues = data.cells
    .map(c => (metric === 'total_cost' ? c.total_cost : c.monthly_installment))
    .filter((v): v is string => v !== null)
    .map(parseFloat)

  const minVal = Math.min(...feasibleValues)
  const maxVal = Math.max(...feasibleValues)

  return (
    <section className="mb-8 border dark:border-gray-700 rounded-xl p-5">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-lg font-semibold">{t('heatmap.title')}</h2>
        <button
          onClick={() => { setData(null); sessionStorage.removeItem(SESSION_HEATMAP_KEY) }}
          className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded"
          aria-label="Close"
        >
          ✕
        </button>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{t('heatmap.subtitle')}</p>

      {/* Metric toggle */}
      <div className="flex gap-2 mb-4">
        {(['total_cost', 'monthly_installment'] as Metric[]).map(m => (
          <button
            key={m}
            onClick={() => setMetric(m)}
            className={`px-3 py-1 text-xs rounded-lg border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-400 ${
              metric === m
                ? 'bg-black text-white dark:bg-white dark:text-black border-black dark:border-white'
                : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800'
            }`}
          >
            {m === 'total_cost' ? t('heatmap.metric_total_cost') : t('heatmap.metric_monthly')}
          </button>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 mb-4 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
        <span>{t('heatmap.legend_low')}</span>
        <div
          className="h-3 w-28 rounded"
          style={{ background: 'linear-gradient(to right, hsl(120,65%,42%), hsl(60,65%,42%), hsl(0,65%,42%))' }}
        />
        <span>{t('heatmap.legend_high')}</span>
        <span className="ml-3 flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-sm border-2 border-blue-500 bg-blue-100 dark:bg-blue-900" />
          {t('heatmap.optimal')}
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-sm bg-gray-200 dark:bg-gray-700" />
          {t('heatmap.infeasible')}
        </span>
      </div>

      {/* Grid */}
      <div className="overflow-x-auto" onMouseLeave={() => setTooltip(null)}>
        {tooltip && (
          <div
            className="fixed z-50 pointer-events-none bg-gray-900 text-white text-xs rounded px-2 py-1 shadow-lg whitespace-nowrap"
            style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
          >
            {tooltip.text}
          </div>
        )}

        <div className="inline-block">
          {/* Duration axis labels */}
          <div className="flex mb-0.5 ml-20">
            {durs.map(dur => (
              <div
                key={dur}
                className="text-center text-xs text-gray-500 dark:text-gray-400 shrink-0"
                style={{ width: 44 }}
              >
                {dur}
              </div>
            ))}
          </div>
          <div className="flex mb-2 ml-20">
            <span className="text-xs text-gray-400 dark:text-gray-500 italic">
              {t('heatmap.duration_axis')}
            </span>
          </div>

          {/* Rows: down payment descending (largest at top) */}
          {[...dps].reverse().map(dp => {
            const dpNum = parseFloat(dp)
            const isOptimalRow = dp === optimalDp
            return (
              <div key={dp} className="flex items-center mb-0.5">
                <div className="w-20 text-right pr-2 text-xs text-gray-500 dark:text-gray-400 shrink-0">
                  {dpNum >= 1000 ? `${(dpNum / 1000).toFixed(0)}k` : dp}
                </div>
                {durs.map(dur => {
                  const cell = index.get(`${dp}:${dur}`)
                  const metricVal = cell
                    ? metric === 'total_cost' ? cell.total_cost : cell.monthly_installment
                    : null
                  const isOptimal = isOptimalRow && dur === optimalDur
                  const bg = metricVal ? cellColor(parseFloat(metricVal), minVal, maxVal) : undefined

                  return (
                    <div
                      key={dur}
                      className={[
                        'rounded-sm cursor-default shrink-0',
                        isOptimal ? 'ring-2 ring-blue-500 ring-offset-1 dark:ring-offset-gray-900 z-10 relative' : '',
                        !metricVal ? 'bg-gray-200 dark:bg-gray-700' : '',
                      ].join(' ')}
                      style={{
                        width: 40,
                        height: 24,
                        marginRight: 4,
                        ...(bg ? { backgroundColor: bg } : {}),
                        opacity: metricVal ? 1 : 0.5,
                      }}
                      onMouseMove={e => {
                        const text = metricVal
                          ? `${fmt(dp, currency)} / ${dur}mo — ${fmt(metricVal, currency)}`
                          : `${fmt(dp, currency)} / ${dur}mo — ${t('heatmap.infeasible')}`
                        setTooltip({ text, x: e.clientX, y: e.clientY })
                      }}
                    />
                  )
                })}
              </div>
            )
          })}

          <div className="mt-1 ml-20 text-xs text-gray-400 dark:text-gray-500 italic">
            ← {t('heatmap.down_payment_axis')}
          </div>
        </div>
      </div>
    </section>
  )
}
