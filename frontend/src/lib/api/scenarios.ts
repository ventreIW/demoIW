import type { ScenarioSummary } from "@/types/scenario"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function listScenarios(): Promise<ScenarioSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios`, { cache: "no-store" })
  if (!res.ok) {
    throw new Error(`Failed to list scenarios: ${res.status}`)
  }
  return res.json()
}

export async function activateScenario(id: string): Promise<ScenarioSummary> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/${id}/activate`, {
    method: "PATCH",
  })
  if (!res.ok) {
    throw new Error(`Failed to activate scenario: ${res.status}`)
  }
  return res.json()
}