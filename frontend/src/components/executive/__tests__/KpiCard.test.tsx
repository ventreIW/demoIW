import { screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import KpiCard from '../KpiCard'

describe('KpiCard', () => {
  it('renders label and formatted currency value (ES locale)', () => {
    renderWithIntl(<KpiCard label="totalOverdue" value={1835177.64} format="currency" />, {
      locale: 'es',
    })

    expect(screen.getByText('Total vencido')).toBeDefined()
    // ES-MX formats as $1,835,178 (comma for thousands, no decimals)
    expect(screen.getByText('$1,835,178')).toBeDefined()
  })

  it('renders label and formatted currency value (EN locale)', () => {
    renderWithIntl(<KpiCard label="totalOverdue" value={1835177.64} format="currency" />, {
      locale: 'en',
    })

    expect(screen.getByText('Total overdue')).toBeDefined()
    // EN-US with MXN currency shows MX$ prefix
    expect(screen.getByText('MX$1,835,178')).toBeDefined()
  })

  it('formats percentage values correctly', () => {
    renderWithIntl(<KpiCard label="recoveryRateActual" value={0.4089} format="percentage" />, {
      locale: 'es',
    })

    expect(screen.getByText('Tasa de recuperación (real)')).toBeDefined()
    // Percentage format: 40.9% (1 decimal)
    expect(screen.getByText('40.9%')).toBeDefined()
  })

  it('formats number values (no currency symbol)', () => {
    renderWithIntl(<KpiCard label="casesByCategory" value={120} format="number" />, {
      locale: 'en',
    })

    expect(screen.getByText('Cases by category')).toBeDefined()
    expect(screen.getByText('120')).toBeDefined()
    // Should not have currency symbol
    expect(screen.queryByText('$120')).toBeNull()
  })

  it('renders subLabel when provided', () => {
    renderWithIntl(<KpiCard label="totalOverdue" value={1000000} subLabel="vs last month" />, {
      locale: 'en',
    })

    expect(screen.getByText('vs last month')).toBeDefined()
  })

  it('handles zero value', () => {
    renderWithIntl(<KpiCard label="totalOverdue" value={0} format="currency" />, {
      locale: 'es',
    })

    expect(screen.getByText('$0')).toBeDefined()
  })

  it('handles large values', () => {
    renderWithIntl(<KpiCard label="totalOverdue" value={1234567890} format="currency" />, {
      locale: 'en',
    })

    expect(screen.getByText('MX$1,234,567,890')).toBeDefined()
  })

  it('applies custom className', () => {
    const { container } = renderWithIntl(
      <KpiCard label="totalOverdue" value={1000} className="custom-class" />,
      { locale: 'en' },
    )

    expect((container.firstChild as HTMLElement).className).toContain('custom-class')
  })
})
