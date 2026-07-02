import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ScenarioSummary } from '@/types/scenario'

vi.mock('@/lib/api/scenarios', () => ({
  uploadCsv: vi.fn(),
  listScenarios: vi.fn(),
  activateScenario: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

import { uploadCsv } from '@/lib/api/scenarios'
import CsvUpload from '../CsvUpload'

const mockUploadCsv = uploadCsv as ReturnType<typeof vi.fn>

const mockScenario: ScenarioSummary = {
  id: '550e8400-e29b-41d4-a716-446655440000',
  name: 'Demo Q3',
  sector: 'retail',
  status: 'inactive',
  client_count: 0,
  created_at: '2026-06-29T10:00:00Z',
}

function createCsvFile(name: string = 'test.csv'): File {
  return new File(['name,sector,client_count\nDemo Q3,retail,3'], name, { type: 'text/csv' })
}

describe('CsvUpload', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders file input with accept=.csv and trigger button', () => {
    render(<CsvUpload onUploadComplete={vi.fn()} />)

    const input = screen.getByLabelText('Seleccionar archivo CSV')
    expect((input as HTMLInputElement).type).toBe('file')
    expect((input as HTMLInputElement).accept).toBe('.csv')

    expect(screen.getByText('Subir CSV')).toBeDefined()
  })

  it('shows selected file name after file selection', () => {
    render(<CsvUpload onUploadComplete={vi.fn()} />)

    const input = screen.getByLabelText('Seleccionar archivo CSV') as HTMLInputElement
    const file = createCsvFile('mi_escenario.csv')
    fireEvent.change(input, { target: { files: [file] } })

    expect(screen.getByText('mi_escenario.csv')).toBeDefined()
    expect(screen.getByText('Subir')).toBeDefined()
  })

  it('disables button and shows loading text during upload', async () => {
    mockUploadCsv.mockImplementation(() => new Promise(() => {}))

    render(<CsvUpload onUploadComplete={vi.fn()} />)

    const input = screen.getByLabelText('Seleccionar archivo CSV') as HTMLInputElement
    fireEvent.change(input, { target: { files: [createCsvFile()] } })

    fireEvent.click(screen.getByText('Subir'))

    await waitFor(() => {
      expect(screen.getByText('Subiendo...')).toBeDefined()
    })

    const button = screen.getByRole('button', { name: 'Subiendo...' })
    expect((button as HTMLButtonElement).disabled).toBe(true)
  })

  it('calls onUploadComplete and shows success message on upload success', async () => {
    mockUploadCsv.mockResolvedValue(mockScenario)
    const onUploadComplete = vi.fn()

    render(<CsvUpload onUploadComplete={onUploadComplete} />)

    const input = screen.getByLabelText('Seleccionar archivo CSV') as HTMLInputElement
    fireEvent.change(input, { target: { files: [createCsvFile()] } })
    fireEvent.click(screen.getByText('Subir'))

    await waitFor(() => {
      expect(onUploadComplete).toHaveBeenCalled()
    })

    expect(screen.getByText(/creado correctamente/)).toBeDefined()
  })

  it('shows error message when upload fails', async () => {
    mockUploadCsv.mockRejectedValue(new Error('Missing required column: sector'))
    const onUploadComplete = vi.fn()

    render(<CsvUpload onUploadComplete={onUploadComplete} />)

    const input = screen.getByLabelText('Seleccionar archivo CSV') as HTMLInputElement
    fireEvent.change(input, { target: { files: [createCsvFile()] } })
    fireEvent.click(screen.getByText('Subir'))

    await waitFor(() => {
      expect(screen.getByText('Missing required column: sector')).toBeDefined()
    })

    expect(onUploadComplete).not.toHaveBeenCalled()
  })
})
