import { screen, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import { portfolioFixture } from '@/test-utils/prioritized-fixture'
import type { ScenarioSummary } from '@/types/scenario'

const getActiveScenario = vi.fn()
const getPrioritized = vi.fn()

vi.mock('@/lib/api/prioritized', () => ({
  getActiveScenario: () => getActiveScenario(),
  getPrioritized: (id: string) => getPrioritized(id),
}))

// MainLayout renders LocaleSwitcher, which needs the app router mounted.
// Same mock the LocaleSwitcher suite uses.
vi.mock('@/i18n/routing', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => '/cases',
}))

// next-intl's server helper is not available in the component test environment;
// the page's strings come from the same catalogue the client provider loads.
vi.mock('next-intl/server', () => ({
  getTranslations: async () => {
    const messages = (await import('../../../../../messages/es.json')).default
    return (key: string) => messages.casesPage[key as keyof typeof messages.casesPage] ?? key
  },
}))

import CasesPage from '../page'

const activeScenario: ScenarioSummary = {
  id: 'scenario-active',
  name: 'Demo retail',
  sector: 'retail',
  status: 'active',
  client_count: 100,
  created_at: '2026-07-28T10:00:00Z',
}

beforeEach(() => {
  vi.clearAllMocks()
})

async function renderPage() {
  renderWithIntl(await CasesPage())
}

describe('CasesPage', () => {
  it('renders the prioritized cases of the active scenario', async () => {
    getActiveScenario.mockResolvedValue(activeScenario)
    getPrioritized.mockResolvedValue(portfolioFixture)

    await renderPage()

    expect(getPrioritized).toHaveBeenCalledWith('scenario-active')
    expect(screen.getByText('Refacciones del Bajío S.A. de C.V.')).toBeDefined()
    expect(screen.getByText('Textiles del Norte')).toBeDefined()
  })

  it('shows the measured concentration summary above the table', async () => {
    getActiveScenario.mockResolvedValue(activeScenario)
    getPrioritized.mockResolvedValue(portfolioFixture)

    await renderPage()

    expect(screen.getByText(portfolioFixture.summary)).toBeDefined()
  })

  it('tells the operator when no scenario is active instead of showing an empty table', async () => {
    getActiveScenario.mockResolvedValue(null)

    await renderPage()

    expect(
      screen.getByText('No hay un escenario activo. Selecciona uno en Escenarios.'),
    ).toBeDefined()
    expect(getPrioritized).not.toHaveBeenCalled()
    expect(screen.queryByRole('table')).toBeNull()
  })

  it('renders an error state when the backend fails, and does not crash', async () => {
    getActiveScenario.mockResolvedValue(activeScenario)
    getPrioritized.mockRejectedValue(new Error('Failed to load prioritized portfolio: 500'))

    await renderPage()

    expect(screen.getByText(/500/)).toBeDefined()
    expect(screen.queryByRole('table')).toBeNull()
  })

  it('renders the empty message when the active scenario has no cases', async () => {
    getActiveScenario.mockResolvedValue(activeScenario)
    getPrioritized.mockResolvedValue({ ...portfolioFixture, cases: [], pareto_subset: [] })

    await renderPage()

    expect(screen.getByText('No hay cuentas por cobrar en el escenario activo.')).toBeDefined()
  })

  it('stays within s5.1 scope: no sort/filter controls and no case links', async () => {
    getActiveScenario.mockResolvedValue(activeScenario)
    getPrioritized.mockResolvedValue(portfolioFixture)

    await renderPage()

    // AC-12 (s5.1): sorting/filtering UI is parked. s5.2 added case detail links.
    const table = screen.getByRole('table')
    expect(within(table).queryAllByRole('combobox')).toHaveLength(0)
    expect(within(table).queryAllByRole('button')).toHaveLength(0)
    // s5.2: each client name is now a link to the case detail page
    const links = within(table).queryAllByRole('link')
    expect(links.length).toBeGreaterThan(0)
    expect(links[0].getAttribute('href')).toMatch(/^\/\w{2}\/cases\//)
  })
})
