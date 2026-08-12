import { screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import NlQueryPanel from '../NlQueryPanel'
import type { NlQueryResponse } from '@/types/nlQuery'

const scenarioId = 'aaaaaaaa-0000-4000-8000-000000000001'

const answerableResponse: NlQueryResponse = {
  answerable: true,
  question: '¿Cuánto está vencido por categoría de score?',
  scenario: { id: scenarioId, name: 'Retail Q3 (manual)', sector: 'retail' },
  scored_at: '2026-08-04T17:04:57.823152+00:00',
  intent: { metric: 'outstanding', group_by: 'score_category', filters: [] },
  result: {
    metric: 'outstanding',
    group_by: 'score_category',
    total: 1835177.64,
    series: [
      { label: 'high', value: 655498.07 },
      { label: 'medium', value: 601234.11 },
      { label: 'low', value: 578445.46 },
    ],
  },
  narrative: 'De los $1,835,178 vencidos en Retail Q3 (manual), $655,498 corresponden a clientes de score alto.',
  reason: null,
  supported: null,
}

const nullNarrativeResponse: NlQueryResponse = {
  ...answerableResponse,
  narrative: null,
}

const refusalResponse: NlQueryResponse = {
  answerable: false,
  question: '¿Qué clientes pagaron tarde en marzo?',
  scenario: { id: scenarioId, name: 'Retail Q3 (manual)', sector: 'retail' },
  scored_at: '2026-08-04T17:04:57.823152+00:00',
  intent: null,
  result: null,
  narrative: null,
  reason: 'out_of_vocabulary',
  supported: {
    metrics: ['outstanding', 'expected_recoverable', 'client_count'],
    dimensions: ['days_overdue_bucket', 'amount_range', 'score_category'],
    filterable: {
      score_category: ['high', 'medium', 'low'],
      days_overdue_bucket: ['0-30', '31-60', '61-90', '90+'],
    },
  },
}

vi.mock('@/lib/api/executive', () => ({
  askQuestion: vi.fn(),
  PortfolioNotScoredError: class PortfolioNotScoredError extends Error {
    constructor(id?: string) {
      super(`Scenario ${id} has no persisted scores. POST /api/v1/scenarios/${id}/score first.`)
      this.name = 'PortfolioNotScoredError'
    }
  },
  ScenarioNotFoundError: class ScenarioNotFoundError extends Error {
    constructor(id?: string) {
      super(`Scenario with id=${id} not found`)
      this.name = 'ScenarioNotFoundError'
    }
  },
}))

import { askQuestion } from '@/lib/api/executive'

const mockedAskQuestion = vi.mocked(askQuestion)

beforeEach(() => {
  vi.clearAllMocks()
})

function submit(question: string) {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: question } })
  fireEvent.click(screen.getByRole('button', { name: /Preguntar/ }))
}

describe('NlQueryPanel', () => {
  it('renders the question input and submit button', () => {
    renderWithIntl(<NlQueryPanel scenarioId={scenarioId} />, { locale: 'es' })

    expect(screen.getByRole('textbox')).toBeDefined()
    expect(screen.getByRole('button', { name: /Preguntar/ })).toBeDefined()
  })

  it('does not submit an empty or whitespace question', () => {
    renderWithIntl(<NlQueryPanel scenarioId={scenarioId} />, { locale: 'es' })

    const value = screen.getByRole('textbox')
    fireEvent.change(value, { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: /Preguntar/ }))

    expect(mockedAskQuestion).not.toHaveBeenCalled()
  })

  it('submits the question and renders the result chart + narrative + citation for answerable=true', async () => {
    mockedAskQuestion.mockResolvedValue(answerableResponse)
    renderWithIntl(<NlQueryPanel scenarioId={scenarioId} />, { locale: 'es' })

    submit('¿Cuánto está vencido por categoría de score?')

    expect(mockedAskQuestion).toHaveBeenCalledWith(
      scenarioId,
      '¿Cuánto está vencido por categoría de score?',
    )

    await waitFor(() => {
      expect(screen.getByText('high')).toBeDefined()
      expect(screen.getByText(/score alto/)).toBeDefined() // narrative
      // citation (scenario name) appears in both narrative and citation — more than one match is fine
      expect(screen.getAllByText(/Retail Q3/).length).toBeGreaterThanOrEqual(2)
    })
  })

  it('renders the chart without a narrative when narrative is null (designed state)', async () => {
    mockedAskQuestion.mockResolvedValue(nullNarrativeResponse)
    renderWithIntl(<NlQueryPanel scenarioId={scenarioId} />, { locale: 'es' })

    submit('¿Cuánto está vencido?')

    await waitFor(() => {
      expect(screen.getByText('high')).toBeDefined()
    })
    // No narrative paragraph rendered — no placeholder/error
    expect(screen.queryByText(/De los/)).toBeNull()
  })

  it('renders an honest refusal with examples from the API supported vocabulary for answerable=false', async () => {
    mockedAskQuestion.mockResolvedValue(refusalResponse)
    renderWithIntl(<NlQueryPanel scenarioId={scenarioId} />, { locale: 'es' })

    submit('¿Qué clientes pagaron tarde en marzo?')

    await waitFor(() => {
      expect(screen.getByText(/No puedo responder/)).toBeDefined()
      // Metrics + dimensions come from the API's supported vocabulary.
      // A metric appears once per list item, so assert across all matches.
      expect(screen.getAllByText(/outstanding/).length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText(/score_category/).length).toBeGreaterThanOrEqual(1)
    })
    // A refusal must not render a chart
    expect(screen.queryByText('high')).toBeNull()
  })

  it('renders an error/retry state when the API call fails', async () => {
    mockedAskQuestion.mockRejectedValue(new Error('Translation unavailable'))
    renderWithIntl(<NlQueryPanel scenarioId={scenarioId} />, { locale: 'es' })

    submit('¿Cuánto está vencido?')

    await waitFor(() => {
      expect(screen.getByText(/Algo salió mal/)).toBeDefined()
      expect(screen.getByRole('button', { name: /Reintentar/ })).toBeDefined()
    })
  })

  it('disables the submit button while a request is in flight', async () => {
    let resolveFn: (v: NlQueryResponse) => void
    mockedAskQuestion.mockImplementation(
      () =>
        new Promise<NlQueryResponse>((resolve) => {
          resolveFn = resolve
        }),
    )
    renderWithIntl(<NlQueryPanel scenarioId={scenarioId} />, { locale: 'es' })

    submit('¿Cuánto está vencido?')

    const button = screen.getByRole('button', { name: /Preguntar/ }) as HTMLButtonElement
    await waitFor(() => expect(button.disabled).toBe(true))
  })
})
