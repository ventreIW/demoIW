import { screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import {
  caseDetailFixture,
  caseDetailNoScoreFixture,
  caseDetailNoCommsFixture,
} from '@/test-utils/case-detail-fixture'
import CaseDetailView from '@/components/cases/CaseDetail'

// useFormatter and useLocale are provided by NextIntlClientProvider in renderWithIntl

describe('CaseDetailView', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the client profile section', () => {
    renderWithIntl(<CaseDetailView detail={caseDetailFixture} />)
    expect(screen.getByText('Refacciones del Bajío S.A. de C.V.')).toBeDefined()
    expect(screen.getByText('Retail company')).toBeDefined()
    expect(screen.getByText('on_time')).toBeDefined()
  })

  it('renders invoices table', () => {
    renderWithIntl(<CaseDetailView detail={caseDetailFixture} />)
    expect(screen.getByText('INV-001')).toBeDefined()
    expect(screen.getByText('INV-002')).toBeDefined()
  })

  it('renders payments table', () => {
    renderWithIntl(<CaseDetailView detail={caseDetailFixture} />)
    expect(screen.getByText('BANK_TRANSFER')).toBeDefined()
    expect(screen.getByText('CASH')).toBeDefined()
  })

  it('renders communications log', () => {
    renderWithIntl(<CaseDetailView detail={caseDetailFixture} />)
    expect(screen.getByText('Estimado cliente, le recordamos su saldo pendiente.')).toBeDefined()
  })

  it('renders the score section', () => {
    renderWithIntl(<CaseDetailView detail={caseDetailFixture} />)
    expect(screen.getByText('78')).toBeDefined() // Math.round(78.4)
    expect(screen.getByText('Alta rotación reciente con saldos grandes.')).toBeDefined()
  })

  it('renders no-score state when score is null', () => {
    renderWithIntl(<CaseDetailView detail={caseDetailNoScoreFixture} />)
    // The noScore key renders "Sin score disponible"
    expect(screen.getByText('Sin score disponible')).toBeDefined()
  })

  it('renders no-comms state when communications is empty', () => {
    renderWithIntl(<CaseDetailView detail={caseDetailNoCommsFixture} />)
    // The noComms key renders "Sin comunicaciones"
    expect(screen.getByText('Sin comunicaciones')).toBeDefined()
  })

  it('renders the contact result form section when scenarioId and clientId are provided', () => {
    renderWithIntl(
      <CaseDetailView
        detail={caseDetailFixture}
        scenarioId="550e8400-e29b-41d4-a716-446655440000"
        clientId="3f2a1b8c-0000-4000-8000-000000000001"
      />,
    )
    expect(screen.getAllByText('Registrar contacto').length).toBe(2)
  })

  it('does not render the contact result form section when scenarioId is not provided', () => {
    renderWithIntl(<CaseDetailView detail={caseDetailFixture} />)
    expect(screen.queryByText('Registrar contacto')).toBeNull()
  })
})
