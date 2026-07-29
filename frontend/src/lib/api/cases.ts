import type { CaseDetail } from '@/types/case-detail'

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