/** Backend API types matching PrioritizedPortfolioResponse in backend/app/routers/scenarios.py */

export type ScoreCategory = 'High' | 'Medium' | 'Low'

export interface PrioritizedCase {
  client_id: string
  client_name: string
  score: number
  /** Outstanding balance in MXN, already net of partial payments. */
  outstanding: number
  /** Maximum days overdue across the client's open invoices. */
  days_overdue: number
  rank: number
  /** outstanding x score/100, in MXN — money, not a weighted index. */
  expected_recoverable: number
  category: ScoreCategory
}

export interface PrioritizedPortfolio {
  cases: PrioritizedCase[]
  /** Smallest prefix of `cases` whose cumulative expected value reaches `threshold`. */
  pareto_subset: PrioritizedCase[]
  threshold: number
  total_expected_recoverable: number
  subset_expected_recoverable: number
  portfolio_count: number
  subset_count: number
  value_share: number
  /** Spanish one-liner stating the measured concentration. Backend-authored. */
  summary: string
}
