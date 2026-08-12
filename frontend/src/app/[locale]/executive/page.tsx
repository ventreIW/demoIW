import { cookies } from 'next/headers'
import { getTranslations } from 'next-intl/server'
import { Link } from '@/i18n/routing'
import MainLayout from '@/components/layout/MainLayout'
import ExecutiveDashboard from '@/components/executive/ExecutiveDashboard'
import NlQueryPanel from '@/components/executive/NlQueryPanel'
import { fetchKpis, PortfolioNotScoredError } from '@/lib/api/executive'
import type { PortfolioKpis } from '@/types/executive'

export default async function ExecutivePage() {
  const t = await getTranslations('executivePage')

  const cookieStore = await cookies()
  const activeId = cookieStore.get('active_scenario_id')?.value ?? null

  let kpis: PortfolioKpis | null = null
  let error: string | null = null
  let isUnscored = false

  if (activeId) {
    try {
      kpis = await fetchKpis(activeId)
    } catch (e) {
      if (e instanceof PortfolioNotScoredError) {
        isUnscored = true
      } else {
        error = e instanceof Error ? e.message : t('errorLoading')
      }
    }
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('title')}</h1>
          <p className="mt-1 text-sm text-slate-500">{t('description')}</p>
        </div>

        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        ) : isUnscored ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-6 text-center">
            <h2 className="text-lg font-semibold text-slate-900">{t('emptyState.title')}</h2>
            <p className="mt-1 text-sm text-slate-600">{t('emptyState.description')}</p>
            <Link
              href="/scenarios"
              className="mt-4 inline-flex h-9 items-center justify-center rounded-lg bg-slate-900 px-4 text-sm font-medium text-white"
            >
              {t('emptyState.cta')}
            </Link>
          </div>
        ) : !activeId ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {t('noActiveScenario')}
          </div>
        ) : (
          <>
            <ExecutiveDashboard kpis={kpis} />
            {activeId && <NlQueryPanel scenarioId={activeId} />}
          </>
        )}
      </div>
    </MainLayout>
  )
}
