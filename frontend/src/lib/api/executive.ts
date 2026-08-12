import type { PortfolioKpis } from '@/types/executive'
import type { NlQueryResponse } from '@/types/nlQuery'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

/** Error raised when scenario has no persisted scores (409) */
export class PortfolioNotScoredError extends Error {
  constructor(scenarioId: string) {
    super(
      `Scenario ${scenarioId} has no persisted scores. POST /api/v1/scenarios/${scenarioId}/score first.`,
    )
    this.name = 'PortfolioNotScoredError'
  }
}

/** Error raised when scenario not found (404) */
export class ScenarioNotFoundError extends Error {
  constructor(scenarioId: string) {
    super(`Scenario with id=${scenarioId} not found`)
    this.name = 'ScenarioNotFoundError'
  }
}

/** Fetch KPI aggregate for a scenario
 *  @throws PortfolioNotScoredError on 409 (unscored scenario)
 *  @throws ScenarioNotFoundError on 404
 *  @throws Error on other HTTP errors
 */
export async function fetchKpis(scenarioId: string): Promise<PortfolioKpis> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/${scenarioId}/kpis`, {
    cache: 'no-store',
  })

  if (!res.ok) {
    if (res.status === 404) {
      throw new ScenarioNotFoundError(scenarioId)
    }
    if (res.status === 409) {
      throw new PortfolioNotScoredError(scenarioId)
    }
    const body = await res.json().catch(() => ({}))
    const messages = body.detail?.map((d: { msg: string }) => d.msg).join(', ')
    throw new Error(messages || `Failed to load KPIs: ${res.status}`)
  }

  return res.json()
}

/** Send a plain-language question and get the typed answer (or honest refusal).
 *
 *  A scenario that has not been scored raises PortfolioNotScoredError (409).
 *  A missing scenario raises ScenarioNotFoundError (404). Other HTTP errors
 *  raise a generic Error with the backend's detail message.
 */
export async function askQuestion(scenarioId: string, question: string): Promise<NlQueryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/scenarios/${scenarioId}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
    cache: 'no-store',
  })

  if (!res.ok) {
    if (res.status === 404) {
      throw new ScenarioNotFoundError(scenarioId)
    }
    if (res.status === 409) {
      throw new PortfolioNotScoredError(scenarioId)
    }
    const body = await res.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : null
    throw new Error(detail || `Failed to answer question: ${res.status}`)
  }

  return res.json()
}
