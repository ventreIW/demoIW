import { screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import { kpisFixture } from '@/test-utils/kpis-fixture'
import ExecutiveDashboard from '../ExecutiveDashboard'

describe('ExecutiveDashboard', () => {
  it('renders the four KPI cards (ES)', () => {
    const { container } = renderWithIntl(<ExecutiveDashboard kpis={kpisFixture} />)

    expect(screen.getByText('Total vencido')).toBeDefined()
    expect(screen.getByText('Recuperable esperado')).toBeDefined()
    expect(screen.getByText('Casos por categoría')).toBeDefined()
    expect(screen.getByText('Tasa de recuperación (real)')).toBeDefined()
    // Sub-labels for cases-by-category and expected recovery rate
    expect(container.textContent).toContain('Alta: 43')
    expect(container.textContent).toContain('Media: 36')
    expect(container.textContent).toContain('Baja: 41')
    expect(container.textContent).toContain('Tasa de recuperación (esperada)')
  })

  it('renders the three segmentation charts (ES)', () => {
    renderWithIntl(<ExecutiveDashboard kpis={kpisFixture} />)

    expect(screen.getByText('Días de atraso')).toBeDefined()
    expect(screen.getByText('Rango de importe')).toBeDefined()
    expect(screen.getByText('Categoría de score')).toBeDefined()
  })

  it('shows the scenario name and scored_at timestamp', () => {
    const { container } = renderWithIntl(<ExecutiveDashboard kpis={kpisFixture} />)

    expect(screen.getByText('Demo retail')).toBeDefined()
    expect(container.textContent).toContain('Calculado el')
  })

  it('shows a loading state', () => {
    renderWithIntl(<ExecutiveDashboard kpis={null} loading />)
    expect(screen.getByText('Cargando panel ejecutivo…')).toBeDefined()
  })

  it('shows an error state', () => {
    renderWithIntl(<ExecutiveDashboard kpis={null} error="boom" />)
    expect(screen.getByText('boom')).toBeDefined()
  })

  it('renders nothing when kpis is null without loading/error', () => {
    const { container } = renderWithIntl(<ExecutiveDashboard kpis={null} />)
    expect(container.textContent ?? '').toBe('')
  })
})
