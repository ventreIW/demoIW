import { screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import ContactResultForm from '@/components/cases/ContactResultForm'

const defaultProps = {
  scenarioId: '550e8400-e29b-41d4-a716-446655440000',
  clientId: '3f2a1b8c-0000-4000-8000-000000000001',
  onSuccess: vi.fn(),
}

const mockRecord = vi.hoisted(() => vi.fn())
vi.mock('@/lib/api/cases', () => ({
  recordContactResult: mockRecord,
}))

beforeEach(() => {
  vi.restoreAllMocks()
  mockRecord.mockReset()
})

describe('ContactResultForm', () => {
  it('renders the form with heading, textarea, and record button', () => {
    renderWithIntl(<ContactResultForm {...defaultProps} />)

    expect(screen.getByRole('heading', { name: 'Registrar contacto' })).toBeDefined()
    expect(screen.getByText('Resultado del contacto')).toBeDefined()
    expect(screen.getByText('Notas (opcional)')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Registrar contacto' })).toBeDefined()
  })

  it('calls recordContactResult on submit and shows success', async () => {
    mockRecord.mockResolvedValue({
      scenario_id: 'test',
      client_id: 'test',
      portfolio: { scores: [] },
    })

    renderWithIntl(<ContactResultForm {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Registrar contacto' }))

    await vi.waitFor(() => {
      expect(mockRecord).toHaveBeenCalledOnce()
    })

    await vi.waitFor(() => {
      expect(screen.getByText('Contacto registrado exitosamente')).toBeDefined()
    })

    expect(defaultProps.onSuccess).toHaveBeenCalledOnce()
  })

  it('shows inline error on API failure', async () => {
    mockRecord.mockRejectedValue(new Error('Invalid contact result type'))

    renderWithIntl(<ContactResultForm {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Registrar contacto' }))

    await vi.waitFor(() => {
      expect(screen.getByText('Invalid contact result type')).toBeDefined()
    })

    expect(defaultProps.onSuccess).not.toHaveBeenCalled()
  })

  it('disables the button while submitting', async () => {
    let resolvePromise: (v: unknown) => void = () => {}
    mockRecord.mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve
      }),
    )

    renderWithIntl(<ContactResultForm {...defaultProps} />)

    const button = screen.getByRole('button', { name: 'Registrar contacto' })
    fireEvent.click(button)

    await vi.waitFor(() => {
      expect((button as HTMLButtonElement).disabled).toBe(true)
    })

    // Resolve the promise
    resolvePromise({
      scenario_id: 'test',
      client_id: 'test',
      portfolio: { scores: [] },
    })
  })
})