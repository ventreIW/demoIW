import type { CaseDetail } from '@/types/case-detail'

/**
 * Pinned test fixture for the case detail aggregate endpoint.
 * Mirrors the backend response shape field-for-field.
 */
export const caseDetailFixture: CaseDetail = {
  client: {
    id: '3f2a1b8c-0000-4000-8000-000000000001',
    name: 'Refacciones del Bajío S.A. de C.V.',
    sector_description: 'Retail company',
    payment_history_pattern: 'on_time',
  },
  score: {
    score_value: 78.4,
    category: 'high',
    explanation: 'Alta rotación reciente con saldos grandes.',
  },
  invoices: [
    {
      folio: 'INV-001',
      amount: 50000.0,
      issue_date: '2026-06-01T00:00:00Z',
      due_date: '2026-07-01T00:00:00Z',
      days_overdue: 27,
      status: 'OVERDUE',
    },
    {
      folio: 'INV-002',
      amount: 12000.0,
      issue_date: '2026-06-15T00:00:00Z',
      due_date: '2026-07-15T00:00:00Z',
      days_overdue: 13,
      status: 'PENDING',
    },
  ],
  payments: [
    {
      amount: 5000.0,
      payment_date: '2026-07-01T00:00:00Z',
      method: 'BANK_TRANSFER',
    },
    {
      amount: 3000.0,
      payment_date: '2026-06-15T00:00:00Z',
      method: 'CASH',
    },
  ],
  communications: [
    {
      id: 'comm-001',
      channel: 'email',
      tone: 'formal',
      draft_text: 'Estimado cliente, le recordamos su saldo pendiente.',
      status: 'draft',
      created_at: '2026-07-20T10:00:00Z',
      // NFR-06 provenance (BUG-08). sent_at is null because this fixture is a draft.
      operator_id: 'demo-operator (unauthenticated)',
      model_used: 'nvidia/nemotron-3-ultra-550b-a55b:free',
      prompt_version: 'v1',
      sent_at: null,
    },
  ],
}

export const caseDetailNoScoreFixture: CaseDetail = {
  ...caseDetailFixture,
  score: null,
}

export const caseDetailNoCommsFixture: CaseDetail = {
  ...caseDetailFixture,
  communications: [],
}
