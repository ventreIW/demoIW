import { describe, it, expect, vi, beforeEach } from 'vitest'
import { generateScenario } from '../scenarios'
import type { ScenarioSummary } from '@/types/scenario'

const API_BASE = 'http://localhost:8000'

const mockSummary: ScenarioSummary = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  name: 'Demo Q3 — Manufacturing',
  sector: 'manufacturing',
  status: 'inactive',
  client_count: 100,
  created_at: '2026-07-14T10:00:00Z',
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('generateScenario', () => {
  it('sends a POST request to /api/v1/scenarios/generate with correct params', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSummary),
    })
    vi.stubGlobal('fetch', fetchMock)

    const params = {
      sector: 'manufacturing' as const,
      client_count: 100,
      invoice_volume: 3,
      amount_mean: 15000,
      amount_std: 8000,
      seed: 42,
      reference_date: null,
    }

    const result = await generateScenario(params)

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/api/v1/scenarios/generate`,
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      }),
    )
    expect(result).toEqual(mockSummary)
  })

  it('works without optional seed parameter', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSummary),
    })
    vi.stubGlobal('fetch', fetchMock)

    const params = {
      sector: 'retail' as const,
      client_count: 50,
      invoice_volume: 5,
      amount_mean: 20000,
      amount_std: 10000,
      reference_date: null,
    }

    const result = await generateScenario(params)

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(result).toEqual(mockSummary)
  })

  it('throws an error with message from response on HTTP error', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: [{ msg: 'sector must be one of: manufacturing, retail, professional_services' }],
        }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const params = {
      sector: 'manufacturing' as const,
      client_count: 100,
      invoice_volume: 3,
      amount_mean: 15000,
      amount_std: 8000,
      reference_date: null,
    }

    await expect(generateScenario(params)).rejects.toThrow(
      'sector must be one of: manufacturing, retail, professional_services',
    )
  })

  it('throws a generic error when response has no detail array', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ message: 'Internal server error' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const params = {
      sector: 'manufacturing' as const,
      client_count: 100,
      invoice_volume: 3,
      amount_mean: 15000,
      amount_std: 8000,
      reference_date: null,
    }

    await expect(generateScenario(params)).rejects.toThrow('Error al generar: 500')
  })
})