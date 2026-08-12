'use client'

import { useLocale } from 'next-intl'
import { useTranslations } from 'next-intl'
import type { QueryResult } from '@/types/nlQuery'

interface QueryResultChartProps {
  result: QueryResult
}

const CURRENCY_METRICS = new Set(['outstanding', 'expected_recoverable'])

/** Locale-aware formatter. Currency for money metrics, plain number for counts. */
function getFormatter(locale: string, currency: boolean) {
  const REGIONAL: Record<string, string> = { es: 'es-MX', en: 'en-US' }
  const region = REGIONAL[locale] ?? locale
  return new Intl.NumberFormat(region, {
    style: currency ? 'currency' : 'decimal',
    currency: 'MXN',
    maximumFractionDigits: 0,
    currencyDisplay: 'symbol',
  })
}

export default function QueryResultChart({ result }: QueryResultChartProps) {
  const locale = useLocale()
  const t = useTranslations('executivePage.query')

  const isCurrency = CURRENCY_METRICS.has(result.metric)
  const format = getFormatter(locale, isCurrency)

  const maxValue = Math.max(...result.series.map((p) => p.value), 0)

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between text-sm">
        <span className="text-xs text-slate-500">{t('total')}</span>
        <span className="font-medium tabular-nums text-slate-700">
          {format.format(result.total)}
        </span>
      </div>
      <div className="space-y-3">
        {result.series.map((point) => {
          const widthPercent = maxValue > 0 ? (point.value / maxValue) * 100 : 0
          return (
            <div key={point.label} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-slate-700">{point.label}</span>
                <span className="tabular-nums text-slate-500">{format.format(point.value)}</span>
              </div>
              <div className="relative h-3 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="bar-fill h-full bg-slate-600 transition-all duration-300"
                  style={{ width: `${widthPercent}%` }}
                />
              </div>
            </div>
          )
        })}
        {result.series.length === 0 && <p className="text-sm text-slate-400">{t('noData')}</p>}
      </div>
    </div>
  )
}
