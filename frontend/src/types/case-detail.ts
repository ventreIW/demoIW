/** Response from GET /scenarios/{id}/clients/{id} — case aggregate. */

export interface ClientProfile {
  id: string
  name: string
  sector_description: string | null
  payment_history_pattern: string
}

export interface InvoiceSummary {
  folio: string
  amount: number
  issue_date: string
  due_date: string
  days_overdue: number
  status: string
}

export interface PaymentSummary {
  amount: number
  payment_date: string
  method: string
}

export interface CommunicationSummary {
  id: string
  channel: string
  tone: string
  draft_text: string
  status: string
  created_at: string
  /**
   * NFR-06 audit provenance. All nullable: records written before the audit fields existed
   * genuinely do not know their provenance, and say so rather than carrying invented values.
   */
  operator_id: string | null
  model_used: string | null
  prompt_version: string | null
  /** When the draft was sent. Null while it is still a draft. */
  sent_at: string | null
}

export interface ScoreSummary {
  score_value: number
  category: string
  explanation: string
}

export interface CaseDetail {
  client: ClientProfile
  score: ScoreSummary | null
  invoices: InvoiceSummary[]
  payments: PaymentSummary[]
  communications: CommunicationSummary[]
}

/** Contact result types accepted by POST /contact-result (mirrors backend ContactResultType). */
export type ContactResultType =
  | 'promise_to_pay'
  | 'partial_payment'
  | 'no_answer'
  | 'disputed'
  | 'paid'

export interface RecordContactResultRequest {
  contact_result: ContactResultType
  notes?: string
}

export interface ClientScoreEntry {
  client_id: string
  client_name: string
  score_value: number
  category: string
  explanation: string
}

export interface RecordContactResultResponse {
  scenario_id: string
  client_id: string
  portfolio: {
    scores: ClientScoreEntry[]
  }
}

/** Request body for POST /communications (generate draft). */
export interface CommunicationRequest {
  channel: string
  tone: string
}
