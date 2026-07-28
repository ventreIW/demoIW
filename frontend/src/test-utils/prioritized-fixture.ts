import type { PrioritizedCase, PrioritizedPortfolio } from '@/types/prioritized'

/**
 * The pinned contract fixture for the prioritized endpoint (s5.1).
 *
 * Mirrors `PrioritizedPortfolioResponse` field-for-field, with the shape asserted
 * server-side by `backend/tests/test_prioritized_endpoint.py`. Kept in one place so
 * the API-client test, the component test, and the page test cannot drift into three
 * different opinions about what the backend sends — the class of seam bug E4's M4
 * checkpoint exists to catch.
 */
export const caseFixture: PrioritizedCase = {
  client_id: '3f2a1b8c-0000-4000-8000-000000000001',
  client_name: 'Refacciones del Bajío S.A. de C.V.',
  score: 78.4,
  outstanding: 184320.5,
  days_overdue: 47,
  rank: 1,
  expected_recoverable: 144507.27,
  category: 'High',
}

export const secondCaseFixture: PrioritizedCase = {
  client_id: '3f2a1b8c-0000-4000-8000-000000000002',
  client_name: 'Textiles del Norte',
  score: 35.2,
  outstanding: 90000,
  days_overdue: 3,
  rank: 2,
  expected_recoverable: 31680,
  category: 'Low',
}

export const portfolioFixture: PrioritizedPortfolio = {
  cases: [caseFixture, secondCaseFixture],
  pareto_subset: [caseFixture],
  threshold: 0.8,
  total_expected_recoverable: 176187.27,
  subset_expected_recoverable: 144507.27,
  portfolio_count: 2,
  subset_count: 1,
  value_share: 0.82,
  summary: '1 de 2 cuentas concentran 82.0% del valor recuperable esperado.',
}
