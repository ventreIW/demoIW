'use client'

import { useLocale } from 'next-intl'
import { useTranslations } from 'next-intl'
import type { SegmentBucket } from '@/types/executive'

interface SegmentationChartProps {
  buckets: SegmentBucket[]
  dimension: 'days_overdue_bucket' | 'amount_range' | 'score_category'
  title?: string
}

/** Map dimension prop to i18n key */
const DIMENSION_KEY: Record<
  'days_overdue_bucket' | 'amount_range' | 'score_category',
  'daysOverdue' | 'amountRange' | 'scoreCategory'
> = {
  days_overdue_bucket: 'daysOverdue',
  amount_range: 'amountRange',
  score_category: 'scoreCategory',
}

/** Shared currency formatter matching CaseTable pattern */
function getCurrencyFormatter(locale: string) {
  const REGIONAL: Record<string, string> = { es: 'es-MX', en: 'en-US' }
  const region = REGIONAL[locale] ?? locale
  return new Intl.NumberFormat(region, {
    style: 'currency',
    currency: 'MXN',
    maximumFractionDigits: 0,
    currencyDisplay: 'symbol',
  })
}

export default function SegmentationChart({ buckets, dimension, title }: SegmentationChartProps) {
  const locale = useLocale()
  const t = useTranslations('executivePage.chart')
  const currency = getCurrencyFormatter(locale)

  // Find max outstanding for proportional bar widths
  const maxOutstanding = Math.max(...buckets.map((b) => b.outstanding), 1)

  const dimensionLabel = t(DIMENSION_KEY[dimension])

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      {title && <h3 className="mb-3 text-sm font-medium text-slate-700">{title}</h3>}
      <p className="mb-3 text-xs text-slate-500">{dimensionLabel}</p>
      <div className="space-y-3">
        {buckets.map((bucket) => {
          const widthPercent = (bucket.outstanding / maxOutstanding) * 100
          return (
            <div key={bucket.label} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span className="font-medium text-slate-700">{bucket.label}</span>
                <span className="text-slate-500">
                  {bucket.client_count} {t('clients')} ·{' '}
                  <span className="font-medium tabular-nums">
                    {currency.format(bucket.outstanding)}
                  </span>
                </span>
              </div>
              <div className="relative h-3 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full bg-slate-600 transition-all duration-300"
                  style={{ width: `${widthPercent}%` }}
                />
                <span className="absolute inset-0 flex items-center justify-end pr-2 text-xs font-medium tabular-nums text-white">
                  {currency.format(bucket.expected_recoverable)} {t('expectedRecoverable')}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
