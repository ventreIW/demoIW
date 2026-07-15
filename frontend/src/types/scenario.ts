/** Backend API types matching Pydantic schemas from backend/app/routers/scenarios.py */

export type Sector = 'manufacturing' | 'retail' | 'professional_services'

export type ScenarioStatus = 'active' | 'inactive'

export interface GenerationParams {
  sector: Sector
  client_count: number
  invoice_volume: number
  amount_mean: number
  amount_std: number
  seed?: number
  reference_date: string | null
}

export interface ScenarioSummary {
  id: string
  name: string
  sector: Sector
  status: ScenarioStatus
  client_count: number
  created_at: string
}
