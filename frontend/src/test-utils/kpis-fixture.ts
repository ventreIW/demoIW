import type { PortfolioKpis } from '@/types/executive'

/** KPI aggregate fixture mirroring the committed s6.1-payload.json structure. */
export const kpisFixture: PortfolioKpis = {
  scenario: { id: 'scenario-active', name: 'Demo retail', sector: 'retail' },
  scored_at: '2026-07-28T18:30:00Z',
  client_count: 120,
  unscored_client_count: 5,
  total_outstanding: 1847177.64,
  total_expected_recoverable: 1013504.0162,
  collected_to_date: 0,
  recovery_rate_actual: 0.118,
  recovery_rate_expected: 0.548,
  cases_by_category: { high: 43, medium: 36, low: 41 },
  segmentation: {
    days_overdue_bucket: [
      { label: '0-30', client_count: 44, outstanding: 170464.97, expected_recoverable: 62593.805555 },
      { label: '31-60', client_count: 8, outstanding: 174903.64, expected_recoverable: 92246.673639 },
      { label: '61-90', client_count: 13, outstanding: 262726.83, expected_recoverable: 145536.499155 },
      { label: '90+', client_count: 55, outstanding: 1227082.2, expected_recoverable: 713107.05778 },
    ],
    amount_range: [
      { label: '$0 – $2,812', client_count: 30, outstanding: 0, expected_recoverable: 0 },
      { label: '> $24,648', client_count: 30, outstanding: 929947.75, expected_recoverable: 538267.958143 },
    ],
    score_category: [
      { label: 'high', client_count: 43, outstanding: 655498.07, expected_recoverable: 549135.107938 },
      { label: 'low', client_count: 41, outstanding: 620270.84, expected_recoverable: 152610.684131 },
    ],
  },
}
