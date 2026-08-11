import { screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import SegmentationChart from '../SegmentationChart'
import type { SegmentBucket } from '@/types/executive'

const mockBuckets: SegmentBucket[] = [
  { label: '0-30', client_count: 44, outstanding: 170464.97, expected_recoverable: 62593.805555 },
  { label: '31-60', client_count: 8, outstanding: 174903.64, expected_recoverable: 92246.673639 },
  { label: '61-90', client_count: 13, outstanding: 262726.83, expected_recoverable: 145536.499155 },
  { label: '90+', client_count: 55, outstanding: 1227082.2, expected_recoverable: 713107.05778 },
]

describe('SegmentationChart', () => {
  it('renders chart title when provided', () => {
    renderWithIntl(
      <SegmentationChart
        buckets={mockBuckets}
        dimension="days_overdue_bucket"
        title="Test Title"
      />,
      { locale: 'es' },
    )

    expect(screen.getByText('Test Title')).toBeDefined()
  })

  it('renders dimension label from i18n', () => {
    renderWithIntl(<SegmentationChart buckets={mockBuckets} dimension="days_overdue_bucket" />, {
      locale: 'es',
    })

    expect(screen.getByText('Días de atraso')).toBeDefined()
  })

  it('renders dimension label in EN', () => {
    renderWithIntl(<SegmentationChart buckets={mockBuckets} dimension="days_overdue_bucket" />, {
      locale: 'en',
    })

    expect(screen.getByText('Days overdue')).toBeDefined()
  })

  it('renders all bucket labels', () => {
    renderWithIntl(<SegmentationChart buckets={mockBuckets} dimension="days_overdue_bucket" />, {
      locale: 'es',
    })

    expect(screen.getByText('0-30')).toBeDefined()
    expect(screen.getByText('31-60')).toBeDefined()
    expect(screen.getByText('61-90')).toBeDefined()
    expect(screen.getByText('90+')).toBeDefined()
  })

  it('renders client counts and outstanding values', () => {
    renderWithIntl(<SegmentationChart buckets={mockBuckets} dimension="days_overdue_bucket" />, {
      locale: 'es',
    })

    // First bucket: 44 clientes · $170,465
    // Client count + label share a span with the value, so match with a regex
    expect(screen.getByText(/44 clientes/)).toBeDefined()
    expect(screen.getByText('$170,465')).toBeDefined()
  })

  it('renders expected recoverable values in bars', () => {
    const { container } = renderWithIntl(
      <SegmentationChart buckets={mockBuckets} dimension="days_overdue_bucket" />,
      { locale: 'es' },
    )

    // Should show expected recoverable in the bar overlay
    // ES locale uses es-MX which shows $ symbol
    // Text is split across text nodes: $62,594 + " Recuperable esperado"
    // Use container to query for text content
    expect(container.textContent).toContain('62,594')
    expect(container.textContent).toContain('Recuperable esperado')
    expect(container.textContent).toContain('92,247')
    expect(container.textContent).toContain('145,536')
    expect(container.textContent).toContain('713,107')
  })

  it('calculates bar widths proportionally to max outstanding', () => {
    const { container } = renderWithIntl(
      <SegmentationChart buckets={mockBuckets} dimension="days_overdue_bucket" />,
      { locale: 'es' },
    )

    const bars = container.querySelectorAll('.h-full.bg-slate-600')
    expect(bars).toHaveLength(4)

    // Max outstanding is 1,227,082.2 (90+ bucket)
    // 90+ bucket should have 100% width
    const bar90 = bars[3] as HTMLElement
    expect(bar90.style.width).toBe('100%')

    // 0-30 bucket: 170,464.97 / 1,227,082.2 ≈ 13.9%
    const bar030 = bars[0] as HTMLElement
    const width030 = parseFloat(bar030.style.width)
    expect(width030).toBeCloseTo(13.9, 0)

    // 31-60 bucket: 174,903.64 / 1,227,082.2 ≈ 14.3%
    const bar3160 = bars[1] as HTMLElement
    const width3160 = parseFloat(bar3160.style.width)
    expect(width3160).toBeCloseTo(14.3, 0)

    // 61-90 bucket: 262,726.83 / 1,227,082.2 ≈ 21.4%
    const bar6190 = bars[2] as HTMLElement
    const width6190 = parseFloat(bar6190.style.width)
    expect(width6190).toBeCloseTo(21.4, 0)
  })

  it('handles empty buckets array', () => {
    renderWithIntl(<SegmentationChart buckets={[]} dimension="days_overdue_bucket" />, {
      locale: 'es',
    })

    // Should render without errors, just empty space
    expect(screen.getByText('Días de atraso')).toBeDefined()
  })

  it('works with amount_range dimension', () => {
    const amountBuckets: SegmentBucket[] = [
      { label: '$0 – $2,812', client_count: 30, outstanding: 0, expected_recoverable: 0 },
      {
        label: '> $24,648',
        client_count: 30,
        outstanding: 929947.75,
        expected_recoverable: 538267.958143,
      },
    ]

    renderWithIntl(<SegmentationChart buckets={amountBuckets} dimension="amount_range" />, {
      locale: 'en',
    })

    expect(screen.getByText('Amount range')).toBeDefined()
    expect(screen.getByText('$0 – $2,812')).toBeDefined()
    expect(screen.getByText('> $24,648')).toBeDefined()
  })

  it('works with score_category dimension', () => {
    const scoreBuckets: SegmentBucket[] = [
      {
        label: 'high',
        client_count: 43,
        outstanding: 655498.07,
        expected_recoverable: 549135.107938,
      },
      {
        label: 'low',
        client_count: 41,
        outstanding: 620270.84,
        expected_recoverable: 152610.684131,
      },
    ]

    renderWithIntl(<SegmentationChart buckets={scoreBuckets} dimension="score_category" />, {
      locale: 'es',
    })

    expect(screen.getByText('Categoría de score')).toBeDefined()
    expect(screen.getByText('high')).toBeDefined()
    expect(screen.getByText('low')).toBeDefined()
  })
})
