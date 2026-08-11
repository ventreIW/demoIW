'use client'

import { useLocale, useTranslations } from 'next-intl'
import KpiCard from './KpiCard'
import SegmentationChart from './SegmentationChart'
import type { PortfolioKpis, CasesByCategory } from '@/types/executive'

interface ExecutiveDashboardProps {
  kpis: PortfolioKpis | null
  loading?: boolean
  error?: string | null
}

const REGIONAL: Record<string, string> = { es: 'es-MX', en: 'en-US' }

/** Locale-aware date formatter matching the regional pattern used by KpiCard/SegmentationChart. */
function getDateFormatter(locale: string) {
  return new Intl.DateTimeFormat(REGIONAL[locale] ?? locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

/** Percentage formatter used for the expected-recovery sub-label. */
function getPercentFormatter(locale: string) {
  return new Intl.NumberFormat(REGIONAL[locale] ?? locale, {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })
}

/** Total cases across the three categories. */
function totalCases(cases: CasesByCategory): number {
  return cases.high + cases.medium + cases.low
}

export default function ExecutiveDashboard({
  kpis,
  loading = false,
  error = null,
}: ExecutiveDashboardProps) {
  const locale = useLocale()
  const t = useTranslations('executivePage')

  if (loading) {
    return <p className="text-sm text-slate-500">{t('loading')}</p>
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
      </div>
    )
  }

  if (!kpis) {
    return null
  }

  const date = getDateFormatter(locale)
  const percent = getPercentFormatter(locale)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-medium text-slate-700">{kpis.scenario.name}</h2>
          <p className="text-xs text-slate-500">
            {t('scoredAt')} {date.format(new Date(kpis.scored_at))}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="totalOverdue" value={kpis.total_outstanding} format="currency" />
        <KpiCard
          label="expectedRecoverable"
          value={kpis.total_expected_recoverable}
          format="currency"
        />
        <KpiCard
          label="casesByCategory"
          value={totalCases(kpis.cases_by_category)}
          format="number"
          subLabel={`${t('kpi.high')}: ${kpis.cases_by_category.high} · ${t('kpi.medium')}: ${kpis.cases_by_category.medium} · ${t('kpi.low')}: ${kpis.cases_by_category.low}`}
        />
        <KpiCard
          label="recoveryRateActual"
          value={kpis.recovery_rate_actual}
          format="percentage"
          subLabel={`${t('kpi.recoveryRateExpected')}: ${percent.format(kpis.recovery_rate_expected)}`}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <SegmentationChart
          buckets={kpis.segmentation.days_overdue_bucket}
          dimension="days_overdue_bucket"
        />
        <SegmentationChart buckets={kpis.segmentation.amount_range} dimension="amount_range" />
        <SegmentationChart buckets={kpis.segmentation.score_category} dimension="score_category" />
      </div>
    </div>
  )
}
