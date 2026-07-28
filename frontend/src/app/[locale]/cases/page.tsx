import { getTranslations } from 'next-intl/server'
import MainLayout from '@/components/layout/MainLayout'
import CaseTable from '@/components/cases/CaseTable'
import { getActiveScenario, getPrioritized } from '@/lib/api/prioritized'
import type { PrioritizedPortfolio } from '@/types/prioritized'

export default async function CasesPage() {
  const t = await getTranslations('casesPage')

  let portfolio: PrioritizedPortfolio | null = null
  let error: string | null = null
  let hasActiveScenario = true

  try {
    const scenario = await getActiveScenario()
    if (scenario === null) {
      hasActiveScenario = false
    } else {
      portfolio = await getPrioritized(scenario.id)
    }
  } catch (e) {
    error = e instanceof Error ? e.message : t('errorLoading')
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
        ) : !hasActiveScenario ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {t('noActiveScenario')}
          </div>
        ) : (
          <>
            {/* Backend-authored: states the measured concentration rather than an
                assumed 20/80, which this generator's data does not support. */}
            <p className="text-sm text-slate-600">{portfolio?.summary}</p>
            <CaseTable cases={portfolio?.cases ?? []} />
          </>
        )}
      </div>
    </MainLayout>
  )
}
