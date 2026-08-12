/** NL Query types — mirror s6.3 NlQueryResponse / CannotAnswerResponse
 *  Read from backend/app/routers/executive.py and answer_nl_query.py
 */
import type { ScenarioRef } from './executive'

export type RefusalReason = 'out_of_vocabulary' | 'translation_failed' | 'translation_unavailable'

export interface SeriesPoint {
  label: string
  value: number
}

export interface QueryResult {
  metric: string
  group_by: string | null
  total: number
  /** Always ≥1 point (a zero bar is a real answer, not a failure). */
  series: SeriesPoint[]
}

export interface SupportedVocabulary {
  metrics: string[]
  dimensions: string[]
  filterable: Record<string, string[]>
}

export interface NlQueryResponse {
  answerable: boolean
  question: string
  scenario: ScenarioRef
  scored_at: string // ISO 8601
  intent: Record<string, unknown> | null
  result: QueryResult | null
  /** May be null on a SUCCESSFUL answer — narration is best-effort. */
  narrative: string | null
  reason: RefusalReason | null
  supported: SupportedVocabulary | null
}
