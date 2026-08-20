import type { ComponentProps } from 'react'
import { screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import { kpisFixture } from '@/test-utils/kpis-fixture'

const getCookie = vi.fn()
const fetchKpis = vi.fn()

vi.mock('@/lib/api/executive', () => ({
  fetchKpis: (id: string) => fetchKpis(id),
  PortfolioNotScoredError: class PortfolioNotScoredError extends Error {
    constructor(id?: string) {
      super(`Scenario ${id} has no persisted scores`)
      this.name = 'PortfolioNotScoredError'
    }
  },
  ScenarioNotFoundError: class ScenarioNotFoundError extends Error {
    constructor(id?: string) {
      super(`Scenario with id=${id} not found`)
      this.name = 'ScenarioNotFoundError'
    }
  },
}))

vi.mock('next/headers', () => ({
  cookies: async () => ({ get: getCookie }),
}))

/** Recursive shape of the message catalogue, so the dotted-key walk below needs no cast. */
type MessageNode = string | { [segment: string]: MessageNode }

// next-intl's server helper is not available in the test environment; the page's
// strings come from the same catalogue the client provider loads.
vi.mock('next-intl/server', () => ({
  getTranslations: async () => {
    const messages = (await import('../../../../../messages/es.json')).default
    const ns: MessageNode = messages.executivePage
    return (key: string) => {
      const resolved = key
        .split('.')
        .reduce<MessageNode | undefined>(
          (node, segment) =>
            node !== undefined && typeof node !== 'string' ? node[segment] : undefined,
          ns,
        )
      // The real getTranslations always yields a string; fall back to the key itself
      // when a lookup lands on a missing leaf or on an intermediate namespace object.
      return typeof resolved === 'string' ? resolved : key
    }
  },
}))

// MainLayout renders LocaleSwitcher, which needs the app router mounted, and the
// page's CTA uses the route-aware Link. Mirror the LocaleSwitcher suite mocks.
vi.mock('@/i18n/routing', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
  usePathname: () => '/executive',
  Link: ({ href, children, ...props }: ComponentProps<'a'>) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}))

import { PortfolioNotScoredError, ScenarioNotFoundError } from '@/lib/api/executive'
import ExecutivePage from '../page'

beforeEach(() => {
  vi.clearAllMocks()
  getCookie.mockReturnValue({ value: 'scenario-active' })
})

async function renderPage() {
  renderWithIntl(await ExecutivePage())
}

describe('ExecutivePage', () => {
  it('renders the full dashboard for a scored scenario', async () => {
    fetchKpis.mockResolvedValue(kpisFixture)
    await renderPage()

    expect(fetchKpis).toHaveBeenCalledWith('scenario-active')
    expect(screen.getByText('Total vencido')).toBeDefined()
    expect(screen.getByText('Días de atraso')).toBeDefined()
  })

  it('shows an actionable empty state with a scoring CTA for an unscored (409) scenario', async () => {
    fetchKpis.mockRejectedValue(new PortfolioNotScoredError('scenario-active'))
    await renderPage()

    expect(screen.getByText('Escenario sin calificar')).toBeDefined()
    const cta = screen.getByText('Calificar este escenario')
    expect(cta.getAttribute('href')).toBe('/scenarios')
  })

  it('shows an error state when the backend fails', async () => {
    fetchKpis.mockRejectedValue(new ScenarioNotFoundError('scenario-active'))
    await renderPage()

    expect(screen.getByText(/not found/)).toBeDefined()
  })

  it('shows a notice when no scenario is active', async () => {
    getCookie.mockReturnValue(undefined)
    await renderPage()

    expect(
      screen.getByText('No hay un escenario activo. Selecciona uno en Escenarios.'),
    ).toBeDefined()
    expect(fetchKpis).not.toHaveBeenCalled()
  })
})
