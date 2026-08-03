import type { CaseDetail, RecordContactResultRequest, RecordContactResultResponse, CommunicationRequest, CommunicationSummary } from '@/types/case-detail'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function getCaseDetail(scenarioId: string, clientId: string): Promise<CaseDetail> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/${scenarioId}/clients/${clientId}`, {
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`Failed to load case detail: ${res.status}`)
  }
  return res.json()
}

export async function recordContactResult(
  scenarioId: string,
  clientId: string,
  payload: RecordContactResultRequest,
): Promise<RecordContactResultResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/scenarios/${scenarioId}/clients/${clientId}/contact-result`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    const message = Array.isArray(detail) && detail[0]?.msg ? detail[0].msg : `Failed to record contact result: ${res.status}`
    throw new Error(message)
  }
  return res.json()
}

export async function generateCommunication(
  scenarioId: string,
  clientId: string,
  payload: CommunicationRequest,
): Promise<CommunicationSummary> {
  const res = await fetch(
    `${API_BASE}/api/v1/scenarios/${scenarioId}/clients/${clientId}/communications`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    const message = Array.isArray(detail) && detail[0]?.msg ? detail[0].msg : `Failed to generate communication: ${res.status}`
    throw new Error(message)
  }
  return res.json()
}

export async function sendCommunication(
  scenarioId: string,
  clientId: string,
  commId: string,
): Promise<CommunicationSummary> {
  const res = await fetch(
    `${API_BASE}/api/v1/scenarios/${scenarioId}/clients/${clientId}/communications/${commId}/send`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
    },
  )
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : `Failed to send communication: ${res.status}`
    throw new Error(message)
  }
  return res.json()
}