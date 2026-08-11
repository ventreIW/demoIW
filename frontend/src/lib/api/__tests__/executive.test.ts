import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchKpis, PortfolioNotScoredError, ScenarioNotFoundError } from '../executive'
import type { PortfolioKpis } from '@/types/executive'

const API_BASE = 'http://localhost:8000'

const mockKpis: PortfolioKpis = {
  scenario: {
    id: 'aaaaaaaa-0000-4000-8000-000000000001',
    name: 'Retail Q3 (manual)',
    sector: 'retail',
  },
  scored_at: '2026-08-04T17:04:57.823152+00:00',
  client_count: 120,
  unscored_client_count: 0,
  total_outstanding: 1835177.64,
  total_expected_recoverable: 1013484.036129,
  collected_to_date: 1269518.21,
  recovery_rate_actual: 0.4089026015221427,
  recovery_rate_expected: 0.5522539148466303,
  cases_by_category: {
    high: 43,
    medium: 36,
    low: 41,
  },
  segmentation: {
    days_overdue_bucket: [
      {
        label: '0-30',
        client_count: 44,
        outstanding: 170464.97,
        expected_recoverable: 62593.805555,
      },
      {
        label: '31-60',
        client_count: 8,
        outstanding: 174903.64,
        expected_recoverable: 92246.673639,
      },
      {
        label: '61-90',
        client_count: 13,
        outstanding: 262726.83,
        expected_recoverable: 145536.499155,
      },
      {
        label: '90+',
        client_count: 55,
        outstanding: 1227082.2,
        expected_recoverable: 713107.05778,
      },
    ],
    amount_range: [
      { label: '$0 – $2,812', client_count: 30, outstanding: 0.0, expected_recoverable: 0.0 },
      {
        label: '$2,812 – $15,131',
        client_count: 30,
        outstanding: 299771.89,
        expected_recoverable: 148241.039795,
      },
      {
        label: '$15,131 – $24,648',
        client_count: 30,
        outstanding: 605458.0,
        expected_recoverable: 326975.038191,
      },
      {
        label: '> $24,648',
        client_count: 30,
        outstanding: 929947.75,
        expected_recoverable: 538267.958143,
      },
    ],
    score_category: [
      {
        label: 'high',
        client_count: 43,
        outstanding: 655498.07,
        expected_recoverable: 549135.107938,
      },
      {
        label: 'medium',
        client_count: 36,
        outstanding: 559408.73,
        expected_recoverable: 311738.24406,
      },
      {
        label: 'low',
        client_count: 41,
        outstanding: 620270.84,
        expected_recoverable: 152610.684131,
      },
    ],
  },
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('fetchKpis', () => {
  it('sends a GET request to /api/v1/scenarios/{id}/kpis and returns typed KPIs', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockKpis),
    })
    vi.stubGlobal('fetch', fetchMock)

    const scenarioId = 'aaaaaaaa-0000-4000-8000-000000000001'
    const result = await fetchKpis(scenarioId)

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/api/v1/scenarios/${scenarioId}/kpis`,
      expect.objectContaining({ cache: 'no-store' }),
    )
    expect(result).toEqual(mockKpis)
    // Type check: ensure all expected fields are present
    expect(result.scenario.id).toBe(scenarioId)
    expect(result.total_outstanding).toBe(1835177.64)
    expect(result.segmentation.days_overdue_bucket).toHaveLength(4)
    expect(result.segmentation.amount_range).toHaveLength(4)
    expect(result.segmentation.score_category).toHaveLength(3)
  })

  it('throws PortfolioNotScoredError on 409 with actionable message', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: () =>
        Promise.resolve({
          detail:
            'Scenario aaaaaaaa-0000-4000-8000-000000000001 has no persisted scores. POST /api/v1/scenarios/aaaaaaaa-0000-4000-8000-000000000001/score first.',
        }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const scenarioId = 'aaaaaaaa-0000-4000-8000-000000000001'
    await expect(fetchKpis(scenarioId)).rejects.toThrow(PortfolioNotScoredError)
    await expect(fetchKpis(scenarioId)).rejects.toThrow(
      'Scenario aaaaaaaa-0000-4000-8000-000000000001 has no persisted scores',
    )
  })

  it('throws ScenarioNotFoundError on 404', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () =>
        Promise.resolve({
          detail: 'Scenario with id=unknown not found',
        }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchKpis('unknown')).rejects.toThrow(ScenarioNotFoundError)
    await expect(fetchKpis('unknown')).rejects.toThrow('Scenario with id=unknown not found')
  })

  it('throws generic error on other HTTP errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ message: 'Internal server error' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchKpis('some-id')).rejects.toThrow('Failed to load KPIs: 500')
  })

  it('throws generic error with detail messages when available', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: [{ msg: 'Invalid scenario ID' }, { msg: 'Malformed request' }],
        }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchKpis('bad-id')).rejects.toThrow('Invalid scenario ID, Malformed request')
  })
})
