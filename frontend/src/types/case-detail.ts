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
  channel: string
  tone: string
  draft_text: string
  status: string
  created_at: string
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