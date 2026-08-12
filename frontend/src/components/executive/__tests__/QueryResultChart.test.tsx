import { screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import QueryResultChart from '../QueryResultChart'
import type { QueryResult } from '@/types/nlQuery'

const currencyResult: QueryResult = {
  metric: 'outstanding',
  group_by: 'score_category',
  total: 1835177.64,
  series: [
    { label: 'high', value: 655498.07 },
    { label: 'medium', value: 601234.11 },
    { label: 'low', value: 578445.46 },
  ],
}

describe('QueryResultChart', () => {
  it('renders every series label and formatted value', () => {
    const { container } = renderWithIntl(<QueryResultChart result={currencyResult} />, {
      locale: 'es',
    })

    expect(screen.getByText('high')).toBeDefined()
    expect(screen.getByText('medium')).toBeDefined()
    expect(screen.getByText('low')).toBeDefined()
    // Currency symbol varies by ICU (JSDOM may render "MX$" vs "$"); match on
    // the numeric part via container.textContent, mirroring SegmentationChart's
    // pattern for symbol-ambiguous values.
    expect(container.textContent).toContain('655,498')
    expect(container.textContent).toContain('601,234')
    expect(container.textContent).toContain('578,445')
  })

  it('renders currency values in EN locale', () => {
    const { container } = renderWithIntl(<QueryResultChart result={currencyResult} />, {
      locale: 'en',
    })

    expect(container.textContent).toContain('655,498')
  })

  it('renders client_count metric as plain numbers, not currency', () => {
    const countResult: QueryResult = {
      metric: 'client_count',
      group_by: 'days_overdue_bucket',
      total: 120,
      series: [
        { label: '0-30', value: 44 },
        { label: '31-60', value: 8 },
        { label: '61-90', value: 13 },
        { label: '90+', value: 55 },
      ],
    }

    renderWithIntl(<QueryResultChart result={countResult} />, { locale: 'es' })

    expect(screen.getByText('0-30')).toBeDefined()
    expect(screen.getByText('44')).toBeDefined()
    expect(screen.getByText('90+')).toBeDefined()
    expect(screen.getByText('55')).toBeDefined()
  })

  it('computes proportional bar widths against the max value', () => {
    const { container } = renderWithIntl(<QueryResultChart result={currencyResult} />, {
      locale: 'es',
    })

    const bars = container.querySelectorAll('.bar-fill')
    expect(bars).toHaveLength(3)

    // Max value is 655,498.07 (high) → 100%
    const barHigh = bars[0] as HTMLElement
    expect(barHigh.style.width).toBe('100%')

    // medium: 601,234.11 / 655,498.07 ≈ 91.7%
    const barMedium = bars[1] as HTMLElement
    const widthMedium = parseFloat(barMedium.style.width)
    expect(widthMedium).toBeCloseTo(91.7, 0)

    // low: 578,445.46 / 655,498.07 ≈ 88.2%
    const barLow = bars[2] as HTMLElement
    const widthLow = parseFloat(barLow.style.width)
    expect(widthLow).toBeCloseTo(88.2, 0)
  })

  it('renders the total', () => {
    const { container } = renderWithIntl(<QueryResultChart result={currencyResult} />, {
      locale: 'es',
    })

    expect(container.textContent).toContain('1,835,178')
  })

  it('handles an empty series without crashing', () => {
    const empty: QueryResult = {
      metric: 'outstanding',
      group_by: null,
      total: 0,
      series: [],
    }

    const { container } = renderWithIntl(<QueryResultChart result={empty} />, { locale: 'es' })

    // A zero total renders (0), and the empty-series message shows.
    expect(container.textContent).toContain('0')
    expect(screen.getByText('No hay datos para mostrar.')).toBeDefined()
  })

  it('handles a single zero-valued point', () => {
    const zero: QueryResult = {
      metric: 'outstanding',
      group_by: 'days_overdue_bucket',
      total: 0,
      series: [{ label: '61-90', value: 0 }],
    }

    const { container } = renderWithIntl(<QueryResultChart result={zero} />, { locale: 'es' })

    expect(screen.getByText('61-90')).toBeDefined()
    // A single zero point renders a zero-width bar, not an error
    const bars = container.querySelectorAll('.bar-fill')
    expect(bars).toHaveLength(1)
  })
})
