import { useTranslations, useLocale } from 'next-intl'
import { cn } from '@/lib/utils'
import type { PrioritizedCase, ScoreCategory } from '@/types/prioritized'

interface CaseTableProps {
  cases: PrioritizedCase[]
}

const CATEGORY_KEY: Record<ScoreCategory, 'categoryHigh' | 'categoryMedium' | 'categoryLow'> = {
  High: 'categoryHigh',
  Medium: 'categoryMedium',
  Low: 'categoryLow',
}

const CATEGORY_STYLE: Record<ScoreCategory, string> = {
  High: 'bg-emerald-100 text-emerald-800',
  Medium: 'bg-amber-100 text-amber-800',
  Low: 'bg-slate-200 text-slate-700',
}

export default function CaseTable({ cases }: CaseTableProps) {
  const t = useTranslations('casesPage')
  const locale = useLocale()

  // Peso amounts formatted for the reader, not hand-rolled with a hardcoded "$".
  // The regional tag matters: bare 'es' is Spain, which groups thousands with "."
  // and renders "184.321 MXN" — wrong for a Mexican receivables book, where the
  // same figure reads "$184,321". Map the UI locale to the region it is written for.
  const REGIONAL: Record<string, string> = { es: 'es-MX', en: 'en-US' }
  const currency = new Intl.NumberFormat(REGIONAL[locale] ?? locale, {
    style: 'currency',
    currency: 'MXN',
    maximumFractionDigits: 0,
  })

  if (cases.length === 0) {
    return (
      <p className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        {t('empty')}
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-slate-600">
          <tr>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('columnRank')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('columnClient')}
            </th>
            <th scope="col" className="px-4 py-3 text-right font-medium">
              {t('columnOutstanding')}
            </th>
            <th scope="col" className="px-4 py-3 text-right font-medium">
              {t('columnDaysOverdue')}
            </th>
            <th scope="col" className="px-4 py-3 text-right font-medium">
              {t('columnScore')}
            </th>
            <th scope="col" className="px-4 py-3 font-medium">
              {t('columnCategory')}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {cases.map((row) => (
            <tr key={row.client_id} className="hover:bg-slate-50">
              <td className="px-4 py-3 tabular-nums text-slate-400">{row.rank}</td>
              <td className="px-4 py-3 font-medium text-slate-900">{row.client_name}</td>
              <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                {currency.format(row.outstanding)}
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                {t('daysUnit', { days: row.days_overdue })}
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-slate-700">
                {Math.round(row.score)}
              </td>
              <td className="px-4 py-3">
                <span
                  className={cn(
                    'inline-flex rounded-full px-2 py-0.5 text-xs font-medium',
                    CATEGORY_STYLE[row.category],
                  )}
                >
                  {t(CATEGORY_KEY[row.category])}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
