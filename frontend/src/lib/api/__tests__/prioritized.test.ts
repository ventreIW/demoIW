import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getActiveScenario, getPrioritized } from '../prioritized'
import { portfolioFixture } from '@/test-utils/prioritized-fixture'
import type { ScenarioSummary } from '@/types/scenario'

const API_BASE = 'http://localhost:8000'

function scenario(id: string, status: ScenarioSummary['status']): ScenarioSummary {
  return {
    id,
    name: `Escenario ${id}`,
    sector: 'retail',
    status,
    client_count: 100,
    created_at: '2026-07-28T10:00:00Z',
  }
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('getPrioritized', () => {
  it('requests the prioritized portfolio for a scenario without caching', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(portfolioFixture),
    })
    vi.stubGlobal('fetch', fetchMock)

    const portfolio = await getPrioritized('scenario-1')

    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/api/v1/scenarios/scenario-1/prioritized`,
      expect.objectContaining({ cache: 'no-store' }),
    )
    expect(portfolio.cases).toHaveLength(2)
    expect(portfolio.summary).toContain('cuentas concentran')
  })

  it('carries the operator-facing fields through unchanged', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(portfolioFixture) }),
    )

    const [first] = (await getPrioritized('scenario-1')).cases

    expect(first.client_name).toBe('Refacciones del Bajío S.A. de C.V.')
    expect(first.days_overdue).toBe(47)
  })

  it('throws when the backend responds with an error status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))

    await expect(getPrioritized('missing')).rejects.toThrow('404')
  })
})

describe('getActiveScenario', () => {
  it('returns the scenario the backend marks active', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([scenario('a', 'inactive'), scenario('b', 'active')]),
      }),
    )

    const active = await getActiveScenario()

    expect(active?.id).toBe('b')
  })

  it('returns null when no scenario is active', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve([scenario('a', 'inactive')]),
      }),
    )

    expect(await getActiveScenario()).toBeNull()
  })

  it('returns null for an empty scenario list rather than throwing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve([]) }))

    expect(await getActiveScenario()).toBeNull()
  })
})
