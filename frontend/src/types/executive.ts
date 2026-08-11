/** Executive Dashboard types — mirrors backend Pydantic schemas from s6.1
 *  Derived from s6.1-payload.json (committed fixture)
 */

export interface ScenarioRef {
  id: string
  name: string
  sector: string
}

export interface SegmentBucket {
  label: string
  client_count: number
  outstanding: number
  expected_recoverable: number
}

export interface Segmentation {
  days_overdue_bucket: SegmentBucket[]
  amount_range: SegmentBucket[]
  score_category: SegmentBucket[]
}

export interface CasesByCategory {
  high: number
  medium: number
  low: number
}

export interface PortfolioKpis {
  scenario: ScenarioRef
  scored_at: string // ISO 8601 timestamp
  client_count: number
  unscored_client_count: number
  total_outstanding: number
  total_expected_recoverable: number
  collected_to_date: number
  recovery_rate_actual: number
  recovery_rate_expected: number
  cases_by_category: CasesByCategory
  segmentation: Segmentation
}
