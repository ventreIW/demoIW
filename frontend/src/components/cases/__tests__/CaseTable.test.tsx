import { screen, within } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import { caseFixture, secondCaseFixture } from '@/test-utils/prioritized-fixture'
import esMessages from '../../../../messages/es.json'
import enMessages from '../../../../messages/en.json'
import CaseTable from '../CaseTable'

const rows = [caseFixture, secondCaseFixture]

describe('CaseTable', () => {
  it('renders one row per case in rank order', () => {
    renderWithIntl(<CaseTable cases={rows} />)

    const bodyRows = screen.getAllByRole('row').slice(1) // drop the header row
    expect(bodyRows).toHaveLength(2)
    expect(within(bodyRows[0]).getByText('Refacciones del Bajío S.A. de C.V.')).toBeDefined()
    expect(within(bodyRows[1]).getByText('Textiles del Norte')).toBeDefined()
  })

  it('shows the five operator-facing fields on a row', () => {
    renderWithIntl(<CaseTable cases={[caseFixture]} />)

    const row = screen.getAllByRole('row')[1]
    expect(within(row).getByText('Refacciones del Bajío S.A. de C.V.')).toBeDefined()
    expect(within(row).getByText('47 d')).toBeDefined() // days overdue
    expect(within(row).getByText('78')).toBeDefined() // score, rounded
    expect(within(row).getByText('Alta')).toBeDefined() // category, localized
    expect(within(row).getByText('$184,321')).toBeDefined() // outstanding, es-MX
  })

  it('groups pesos the Mexican way, not the Spanish way', () => {
    // Bare 'es' would render "184.321 MXN" — Spain's separators on a Mexican book.
    renderWithIntl(<CaseTable cases={[caseFixture]} />)

    expect(screen.getByText('$184,321')).toBeDefined()
    expect(screen.queryByText('184.321 MXN')).toBeNull()
  })

  it('never shows a raw client id — a UUID cannot be phoned', () => {
    renderWithIntl(<CaseTable cases={rows} />)

    expect(screen.queryByText(caseFixture.client_id)).toBeNull()
  })

  it('localizes the category badge instead of leaking the English enum', () => {
    renderWithIntl(<CaseTable cases={rows} />)

    expect(screen.getByText('Alta')).toBeDefined()
    expect(screen.getByText('Baja')).toBeDefined()
    expect(screen.queryByText('High')).toBeNull()
    expect(screen.queryByText('Low')).toBeNull()
  })

  it('renders the English category labels under the en locale', () => {
    renderWithIntl(<CaseTable cases={rows} />, { locale: 'en' })

    expect(screen.getByText('High')).toBeDefined()
    expect(screen.getByText('Low')).toBeDefined()
  })

  it('renders the empty message rather than a blank table', () => {
    renderWithIntl(<CaseTable cases={[]} />)

    expect(screen.getByText('No hay cuentas por cobrar en el escenario activo.')).toBeDefined()
    expect(screen.queryByRole('table')).toBeNull()
  })
})

describe('message catalogue', () => {
  it('keeps es and en key sets identical', () => {
    const keys = (obj: Record<string, unknown>, prefix = ''): string[] =>
      Object.entries(obj).flatMap(([key, value]) =>
        value !== null && typeof value === 'object'
          ? [prefix + key, ...keys(value as Record<string, unknown>, `${prefix}${key}.`)]
          : [prefix + key],
      )

    expect(keys(esMessages).sort()).toEqual(keys(enMessages).sort())
  })
})
