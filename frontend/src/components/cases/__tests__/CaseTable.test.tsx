import { screen, within } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import { caseFixture, secondCaseFixture } from '@/test-utils/prioritized-fixture'
import esMessages from '../../../../messages/es.json'
import enMessages from '../../../../messages/en.json'
import CaseTable from '../CaseTable'
import type { ScoreCategory } from '@/types/prioritized'

// next/link is a client component that renders an <a> tag in tests
vi.mock('next/link', () => ({
  default: ({
    children,
    href,
    className,
  }: {
    children: React.ReactNode
    href: string
    className?: string
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}))

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

  it('renders a label for every category the backend can send', () => {
    // The live payload serializes ScoreCategory as lowercase ("high"), not "High".
    // Typing it capitalized made CATEGORY_KEY[row.category] undefined and the badge
    // blank — a seam bug the mocked tests could not see, because the fixture shared
    // the same wrong assumption. Enumerate the real values so a recurrence fails here.
    const categories: ScoreCategory[] = ['high', 'medium', 'low']
    const cases = categories.map((category, i) => ({
      ...caseFixture,
      client_id: `case-${i}`,
      rank: i + 1,
      category,
    }))

    renderWithIntl(<CaseTable cases={cases} />)

    expect(screen.getByText('Alta')).toBeDefined()
    expect(screen.getByText('Media')).toBeDefined()
    expect(screen.getByText('Baja')).toBeDefined()
  })

  it('renders the empty message rather than a blank table', () => {
    renderWithIntl(<CaseTable cases={[]} />)

    expect(screen.getByText('No hay cuentas por cobrar en el escenario activo.')).toBeDefined()
    expect(screen.queryByRole('table')).toBeNull()
  })

  it('wraps each client name in a link to the case detail page', () => {
    renderWithIntl(<CaseTable cases={[caseFixture]} />)

    const link = screen.getByRole('link', { name: caseFixture.client_name })
    expect(link).toBeDefined()
    expect(link.getAttribute('href')).toBe(`/es/cases/${caseFixture.client_id}`)
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
