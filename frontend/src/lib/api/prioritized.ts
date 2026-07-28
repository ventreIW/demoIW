import type { PrioritizedPortfolio } from '@/types/prioritized'
import type { ScenarioSummary } from '@/types/scenario'
import { listScenarios } from './scenarios'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

/**
 * The scenario the operations panel works against.
 *
 * Resolved from the backend's persisted `status`, not from the `active_scenario_id`
 * cookie the scenarios page sets: `PATCH /activate` is what durably marks a scenario
 * active, so it is the truth a fresh browser or a second device also sees.
 * Reconciling the cookie is parked (s5.1 design, finding 5).
 */
export async function getActiveScenario(): Promise<ScenarioSummary | null> {
  const scenarios = await listScenarios()
  return scenarios.find((scenario) => scenario.status === 'active') ?? null
}

export async function getPrioritized(scenarioId: string): Promise<PrioritizedPortfolio> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/${scenarioId}/prioritized`, {
    cache: 'no-store',
  })
  if (!res.ok) {
    throw new Error(`Failed to load prioritized portfolio: ${res.status}`)
  }
  return res.json()
}
