import { describe, it, expect, vi, beforeEach } from 'vitest'
import { recordContactResult, generateCommunication, sendCommunication } from '../cases'

const API_BASE = 'http://localhost:8000'

const mockResponse = {
  scenario_id: '550e8400-e29b-41d4-a716-446655440000',
  client_id: '3f2a1b8c-0000-4000-8000-000000000001',
  portfolio: {
    scores: [
      {
        client_id: '3f2a1b8c-0000-4000-8000-000000000001',
        client_name: 'Refacciones del Bajío S.A. de C.V.',
        score_value: 88.4,
        category: 'high',
        explanation: 'Updated score after contact.',
      },
    ],
  },
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('recordContactResult', () => {
  it('sends a POST request to the contact-result endpoint with correct body', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })
    vi.stubGlobal('fetch', fetchMock)

    const scenarioId = '550e8400-e29b-41d4-a716-446655440000'
    const clientId = '3f2a1b8c-0000-4000-8000-000000000001'
    const payload = {
      contact_result: 'promise_to_pay' as const,
      notes: 'Client will pay Friday',
    }

    const result = await recordContactResult(scenarioId, clientId, payload)

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/api/v1/scenarios/${scenarioId}/clients/${clientId}/contact-result`,
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    )
    expect(result).toEqual(mockResponse)
  })

  it('works without optional notes', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })
    vi.stubGlobal('fetch', fetchMock)

    const scenarioId = '550e8400-e29b-41d4-a716-446655440000'
    const clientId = '3f2a1b8c-0000-4000-8000-000000000001'

    const result = await recordContactResult(scenarioId, clientId, {
      contact_result: 'no_answer',
    })

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(result).toEqual(mockResponse)
  })

  it('throws an error with message from response on HTTP error', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: [{ msg: 'Invalid contact_result: not_a_valid_type' }],
        }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      recordContactResult('scenario-id', 'client-id', {
        contact_result: 'promise_to_pay' as const,
      }),
    ).rejects.toThrow('Invalid contact_result: not_a_valid_type')
  })

  it('throws a generic error when response has no detail array', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ message: 'Internal server error' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      recordContactResult('scenario-id', 'client-id', {
        contact_result: 'promise_to_pay' as const,
      }),
    ).rejects.toThrow('Failed to record contact result: 500')
  })
})

describe('generateCommunication', () => {
  it('sends a POST request to the communications endpoint with channel and tone', async () => {
    const mockDraft = {
      id: 'comm-001',
      channel: 'email',
      tone: 'formal',
      draft_text: 'Estimado cliente, le recordamos su saldo pendiente.',
      status: 'draft',
      created_at: '2026-08-02T10:00:00Z',
    }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDraft),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await generateCommunication('scenario-1', 'client-1', {
      channel: 'email',
      tone: 'formal',
    })

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/api/v1/scenarios/scenario-1/clients/client-1/communications`,
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: 'email', tone: 'formal' }),
      }),
    )
    expect(result).toEqual(mockDraft)
  })

  it('throws an error on 422 response', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: () =>
        Promise.resolve({
          detail: [{ msg: 'Invalid channel: not_a_valid_channel' }],
        }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(
      generateCommunication('scenario-1', 'client-1', {
        channel: 'not_a_valid_channel' as 'email' | 'sms' | 'whatsapp',
        tone: 'formal',
      }),
    ).rejects.toThrow('Invalid channel: not_a_valid_channel')
  })
})

describe('sendCommunication', () => {
  it('sends a PATCH request to the send endpoint', async () => {
    const mockSent = {
      id: 'comm-001',
      channel: 'email',
      tone: 'formal',
      draft_text: 'Estimado cliente, le recordamos su saldo pendiente.',
      status: 'sent',
      created_at: '2026-08-02T10:00:00Z',
    }
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockSent),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await sendCommunication('scenario-1', 'client-1', 'comm-001')

    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/api/v1/scenarios/scenario-1/clients/client-1/communications/comm-001/send`,
      expect.objectContaining({
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    expect(result).toEqual(mockSent)
  })

  it('throws an error on 409 conflict', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: () =>
        Promise.resolve({
          detail: 'Communication is not in draft status',
        }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await expect(sendCommunication('scenario-1', 'client-1', 'comm-001')).rejects.toThrow(
      'Communication is not in draft status',
    )
  })
})
