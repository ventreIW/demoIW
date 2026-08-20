import { describe, it, expect, vi } from 'vitest'
import { runAxeOn } from '@/test-utils/a11y'
import { kpisFixture } from '@/test-utils/kpis-fixture'
import { caseFixture, secondCaseFixture } from '@/test-utils/prioritized-fixture'
import { caseDetailFixture } from '@/test-utils/case-detail-fixture'
import CaseTable from '@/components/cases/CaseTable'
import CaseDetailView from '@/components/cases/CaseDetail'
import KpiCard from '@/components/executive/KpiCard'
import ExecutiveDashboard from '@/components/executive/ExecutiveDashboard'
import LocaleSwitcher from '@/components/locale/LocaleSwitcher'
import CsvUpload from '@/components/scenarios/CsvUpload'
import ScenarioCard from '@/components/scenarios/ScenarioCard'

// CsvUpload imports uploadCsv; mock it
vi.mock('@/lib/api/scenarios', () => ({
  uploadCsv: vi.fn(),
}))

// LocaleSwitcher imports @/i18n/routing; mock globally for any component
// that may transitively import it
vi.mock('@/i18n/routing', () => ({
  useRouter: vi.fn(() => ({ replace: vi.fn(), push: vi.fn() })),
  usePathname: vi.fn(() => '/cases'),
}))

const activeScenario = {
  id: 'scenario-active',
  name: 'Demo retail',
  sector: 'retail' as const,
  client_count: 120,
  status: 'active' as const,
  created_at: '2026-07-28T18:30:00Z',
}

const promoScenario = {
  id: 'scenario-2',
  name: 'Manufacturing',
  sector: 'manufacturing' as const,
  client_count: 200,
  status: 'active' as const,
  created_at: '2026-07-29T18:30:00Z',
}

describe('a11y scan — WCAG 2.1 AA semantic rules (jsdom)', () => {
  it('CaseTable — 0 AA violations', async () => {
    const r = await runAxeOn(
      <CaseTable cases={[caseFixture, secondCaseFixture]} />,
      { locale: 'es' },
    )
    expect(r.violations).toEqual([])
  })

  // caseDetailFixture was imported by s7.2 but never scanned — CaseDetail is a primary
  // operator surface, so the omission left a real gap in the "9 components" claim.
  it('CaseDetail — 0 AA violations', async () => {
    const r = await runAxeOn(<CaseDetailView detail={caseDetailFixture} />, { locale: 'es' })
    expect(r.violations).toEqual([])
  })

  it('KpiCard — 0 AA violations', async () => {
    const r = await runAxeOn(
      <KpiCard label="totalOverdue" value={1835177.64} format="currency" subLabel="vs last month" />,
      { locale: 'es' },
    )
    expect(r.violations).toEqual([])
  })

  it('ExecutiveDashboard — 0 AA violations (with data)', async () => {
    const r = await runAxeOn(
      <ExecutiveDashboard kpis={kpisFixture} />,
      { locale: 'es' },
    )
    expect(r.violations).toEqual([])
  })

  it('ExecutiveDashboard — 0 AA violations (loading)', async () => {
    const r = await runAxeOn(
      <ExecutiveDashboard kpis={null} loading />,
      { locale: 'es' },
    )
    expect(r.violations).toEqual([])
  })

  it('ExecutiveDashboard — 0 AA violations (error)', async () => {
    const r = await runAxeOn(
      <ExecutiveDashboard kpis={null} error="API error" />,
      { locale: 'es' },
    )
    expect(r.violations).toEqual([])
  })

  it('LocaleSwitcher — 0 AA violations', async () => {
    const r = await runAxeOn(<LocaleSwitcher />, { locale: 'es' })
    expect(r.violations).toEqual([])
  })

  it('CsvUpload — 0 AA violations (initial state)', async () => {
    const r = await runAxeOn(<CsvUpload onUploadComplete={() => {}} />, { locale: 'es' })
    expect(r.violations).toEqual([])
  })

  it('ScenarioCard (active) — 0 AA violations', async () => {
    const r = await runAxeOn(
      <ScenarioCard
        scenario={activeScenario}
        isActive
        onActivate={() => Promise.resolve()}
        isActivating={false}
      />,
      { locale: 'es' },
    )
    expect(r.violations).toEqual([])
  })

  it('ScenarioCard (with data) — 0 AA violations', async () => {
    const r = await runAxeOn(
      <ScenarioCard
        scenario={promoScenario}
        isActive={false}
        onActivate={() => Promise.resolve()}
        isActivating={false}
      />,
      { locale: 'es' },
    )
    expect(r.violations).toEqual([])
  })
})