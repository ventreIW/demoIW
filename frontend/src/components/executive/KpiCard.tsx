'use client'

import { useLocale } from 'next-intl'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'

interface KpiCardProps {
  label: string
  value: number
  format?: 'currency' | 'number' | 'percentage'
  subLabel?: string
  className?: string
}

/** Shared currency/number formatter matching CaseTable pattern */
function getFormatter(locale: string, format: 'currency' | 'number' | 'percentage') {
  const REGIONAL: Record<string, string> = { es: 'es-MX', en: 'en-US' }
  const region = REGIONAL[locale] ?? locale

  if (format === 'currency') {
    // Use currencyDisplay: 'symbol' to show $ instead of MX$ for en-US
    return new Intl.NumberFormat(region, {
      style: 'currency',
      currency: 'MXN',
      maximumFractionDigits: 0,
      currencyDisplay: 'symbol',
    })
  }
  if (format === 'percentage') {
    return new Intl.NumberFormat(region, {
      style: 'percent',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })
  }
  return new Intl.NumberFormat(region, {
    maximumFractionDigits: 0,
  })
}

export default function KpiCard({
  label,
  value,
  format = 'currency',
  subLabel,
  className,
}: KpiCardProps) {
  const locale = useLocale()
  const t = useTranslations('executivePage.kpi')
  const formatter = getFormatter(locale, format)

  const formattedValue = format === 'percentage' ? formatter.format(value) : formatter.format(value)

  return (
    <div className={cn('rounded-lg border border-slate-200 bg-white p-4 shadow-sm', className)}>
      <p className="text-sm text-slate-500">{t(label)}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{formattedValue}</p>
      {subLabel && <p className="mt-1 text-xs text-slate-500">{subLabel}</p>}
    </div>
  )
}
