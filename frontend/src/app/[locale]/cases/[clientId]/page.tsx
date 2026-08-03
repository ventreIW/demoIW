import { getActiveScenario } from '@/lib/api/prioritized'
import { getCaseDetail } from '@/lib/api/cases'
import { getTranslations } from 'next-intl/server'
import MainLayout from '@/components/layout/MainLayout'
import CaseDetailView from '@/components/cases/CaseDetail'
import Link from 'next/link'

export default async function CaseDetailPage({
  params,
}: {
  params: Promise<{ clientId: string; locale: string }>
}) {
  const { clientId } = await params
  const t = await getTranslations('caseDetail')

  let detail = null
  let error: string | null = null
  let noActiveScenario = false
  let scenario: { id: string } | null = null

  try {
    scenario = await getActiveScenario()
    if (scenario === null) {
      noActiveScenario = true
    } else {
      detail = await getCaseDetail(scenario.id, clientId)
    }
  } catch (e) {
    error = e instanceof Error ? e.message : t('errorLoading')
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/cases" className="text-sm text-slate-500 hover:text-slate-800">
            {t('backToCases')}
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">{t('title')}</h1>
          </div>
        </div>

        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
            <div className="mt-2">
              <Link href="/cases" className="underline hover:no-underline">
                {t('backToCasesLink')}
              </Link>
            </div>
          </div>
        ) : noActiveScenario ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            {t('noScore')}
          </div>
        ) : detail && scenario ? (
          <CaseDetailView detail={detail} scenarioId={scenario.id} clientId={clientId} />
        ) : null}
      </div>
    </MainLayout>
  )
}
