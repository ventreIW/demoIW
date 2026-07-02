/** Backend API types matching Pydantic schemas from backend/app/routers/scenarios.py */

export type Sector = 'manufacturing' | 'retail' | 'professional_services'

export type ScenarioStatus = 'active' | 'inactive'

export interface ScenarioSummary {
  id: string
  name: string
  sector: Sector
  status: ScenarioStatus
  client_count: number
  created_at: string
}
