import { cookies } from 'next/headers'
import { getTranslations } from 'next-intl/server'
import MainLayout from '@/components/layout/MainLayout'
import ScenarioGrid from '@/components/scenarios/ScenarioGrid'
import CsvUploadWrapper from './CsvUploadWrapper'
import { listScenarios } from '@/lib/api/scenarios'
import type { ScenarioSummary } from '@/types/scenario'

export default async function ScenariosPage() {
  const t = await getTranslations('scenariosPage')
  let scenarios: ScenarioSummary[] = []
  let error: string | null = null

  try {
    scenarios = await listScenarios()
  } catch (e) {
    error = e instanceof Error ? e.message : t('errorLoading')
  }

  const cookieStore = await cookies()
  const activeId = cookieStore.get('active_scenario_id')?.value ?? null

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('title')}</h1>
          <p className="mt-1 text-sm text-slate-500">
            {t('description')}
          </p>
        </div>

        {error ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        ) : (
          <ScenarioGrid scenarios={scenarios} activeId={activeId} />
        )}

        <div className="flex gap-3">
          <button
            disabled
            className="inline-flex h-8 items-center justify-center rounded-lg border border-transparent bg-slate-200 px-3 text-sm font-medium text-slate-500 opacity-50"
          >
            {t('generateNew')}
          </button>
          <CsvUploadWrapper />
        </div>
      </div>
    </MainLayout>
  )
}