import { screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import type { ScenarioSummary } from '@/types/scenario'

const mockPush = vi.fn()
const mockReplace = vi.fn()

vi.mock('@/lib/api/scenarios', () => ({
  generateScenario: vi.fn(),
  activateScenario: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}))

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

import { generateScenario, activateScenario } from '@/lib/api/scenarios'
import GenerateScenarioForm from '../GenerateScenarioForm'
import { toast } from 'sonner'

const mockGenerateScenario = generateScenario as ReturnType<typeof vi.fn>
const mockActivateScenario = activateScenario as ReturnType<typeof vi.fn>
const mockToastError = toast.error as ReturnType<typeof vi.fn>

const mockScenario: ScenarioSummary = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  name: 'Demo Escenario',
  sector: 'manufacturing',
  status: 'inactive',
  client_count: 100,
  created_at: '2026-07-14T10:00:00Z',
}

function submitForm() {
  const form = document.querySelector('form')!
  fireEvent.submit(form)
}

describe('GenerateScenarioForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders form fields: sector, client count, invoice volume, seed', () => {
    renderWithIntl(<GenerateScenarioForm />)

    expect(screen.getByText('Sector')).toBeDefined()
    expect(screen.getByText(/número de clientes/i)).toBeDefined()
    expect(screen.getByText(/facturas por cliente/i)).toBeDefined()
    expect(screen.getByText(/semilla \(opcional\)/i)).toBeDefined()
    expect(screen.getByText(/generar escenario/i)).toBeDefined()
  })

  it('shows loading state on submit', async () => {
    mockGenerateScenario.mockImplementation(() => new Promise(() => {}))
    const { container } = renderWithIntl(<GenerateScenarioForm />)

    submitForm()

    await waitFor(() => {
      const button = screen.getByRole('button', { name: /generando datos/i })
      expect((button as HTMLButtonElement).disabled).toBe(true)
    })

    expect(container.querySelector('.animate-spin')).toBeDefined()
  })

  it('displays scenario details on success', async () => {
    mockGenerateScenario.mockResolvedValue(mockScenario)
    renderWithIntl(<GenerateScenarioForm />)

    submitForm()

    await waitFor(() => {
      expect(screen.getByText('Demo Escenario')).toBeDefined()
    })

    expect(screen.getAllByText(/manufacturing/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('100').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText(/Inactivo/)).toBeDefined()
    expect(screen.getByText(/Activar y usar/)).toBeDefined()
  })

  it('shows download link pointing to correct endpoint', async () => {
    mockGenerateScenario.mockResolvedValue(mockScenario)
    renderWithIntl(<GenerateScenarioForm />)

    submitForm()

    await waitFor(() => {
      expect(screen.getByText('Demo Escenario')).toBeDefined()
    })

    const downloadLink = screen.getByRole('link', { name: /descargar/i })
    expect(downloadLink).toBeDefined()
    expect(downloadLink.getAttribute('href')).toContain(
      `/api/v1/scenarios/${mockScenario.id}/download`,
    )
  })

  it('calls activateScenario and redirects on "Activar y usar" click', async () => {
    mockGenerateScenario.mockResolvedValue(mockScenario)
    mockActivateScenario.mockResolvedValue(mockScenario)

    renderWithIntl(<GenerateScenarioForm />)

    submitForm()

    await waitFor(() => {
      expect(screen.getByText('Demo Escenario')).toBeDefined()
    })

    fireEvent.click(screen.getByText('Activar y usar'))

    await waitFor(() => {
      expect(mockActivateScenario).toHaveBeenCalledWith(mockScenario.id)
      expect(mockPush).toHaveBeenCalledWith('/operations')
    })
  })

  it('shows error message on generation failure', async () => {
    mockGenerateScenario.mockRejectedValue(new Error('El sector no es válido'))
    renderWithIntl(<GenerateScenarioForm />)

    submitForm()

    await waitFor(() => {
      expect(mockToastError).toHaveBeenCalledWith('El sector no es válido')
    })
  })

  it('appends scenario ID to URL on success', async () => {
    mockGenerateScenario.mockResolvedValue(mockScenario)
    renderWithIntl(<GenerateScenarioForm />)

    submitForm()

    await waitFor(() => {
      expect(screen.getByText('Demo Escenario')).toBeDefined()
    })

    expect(mockReplace).toHaveBeenCalledWith(
      expect.stringContaining(`scenarioId=${mockScenario.id}`),
      expect.any(Object),
    )
  })

  it('copies scenario ID to clipboard on button click', async () => {
    const writeText = vi.fn()
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      writable: true,
      configurable: true,
    })

    mockGenerateScenario.mockResolvedValue(mockScenario)
    renderWithIntl(<GenerateScenarioForm />)

    submitForm()

    await waitFor(() => {
      expect(screen.getByText('Demo Escenario')).toBeDefined()
    })

    const copyButton = screen.getByRole('button', { name: /copiar/i })
    fireEvent.click(copyButton)

    expect(writeText).toHaveBeenCalledWith(mockScenario.id)
  })

  it('has min=200 on client count input', () => {
    renderWithIntl(<GenerateScenarioForm />)
    const input = screen.getByLabelText(/número de clientes/i) as HTMLInputElement
    expect(input.min).toBe('200')
  })
})
