import type { GenerationParams, ScenarioSummary } from '@/types/scenario'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function listScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios`, { cache: 'no-store' })
  if (!res.ok) {
    throw new Error(`Failed to list scenarios: ${res.status}`)
  }
  return res.json()
}

export async function generateScenario(params: GenerationParams): Promise<ScenarioSummary> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) {
    const body = await res.json()
    const messages = body.detail?.map((d: { msg: string }) => d.msg).join(', ')
    throw new Error(messages || `Error al generar: ${res.status}`)
  }
  return res.json()
}

export async function activateScenario(id: string): Promise<ScenarioSummary> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/${id}/activate`, {
    method: 'PATCH',
  })
  if (!res.ok) {
    throw new Error(`Failed to activate scenario: ${res.status}`)
  }
  return res.json()
}

export async function uploadCsv(file: File): Promise<ScenarioSummary> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/v1/scenarios/upload-csv`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const body = await res.json()
    const messages = body.detail?.map((d: { msg: string }) => d.msg).join(', ')
    throw new Error(messages || `Error al subir: ${res.status}`)
  }
  return res.json()
}
