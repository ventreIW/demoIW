import { screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import CommunicationsGenerator from '@/components/cases/CommunicationsGenerator'

const defaultProps = {
  scenarioId: '550e8400-e29b-41d4-a716-446655440000',
  clientId: '3f2a1b8c-0000-4000-8000-000000000001',
}

const mockGenerate = vi.hoisted(() => vi.fn())
const mockSend = vi.hoisted(() => vi.fn())

vi.mock('@/lib/api/cases', () => ({
  generateCommunication: mockGenerate,
  sendCommunication: mockSend,
}))

const mockDraftResponse = {
  id: 'comm-001',
  channel: 'email',
  tone: 'formal',
  draft_text: 'Estimado cliente, le recordamos su saldo pendiente.',
  status: 'draft',
  created_at: '2026-08-02T10:00:00Z',
}

const mockSentResponse = {
  ...mockDraftResponse,
  status: 'sent',
}

beforeEach(() => {
  vi.restoreAllMocks()
  mockGenerate.mockReset()
  mockSend.mockReset()
  // Mock window.confirm to return true by default
  vi.stubGlobal('confirm', vi.fn(() => true))
})

describe('CommunicationsGenerator', () => {
  it('renders the section title, channel/tone selectors, and generate button', () => {
    renderWithIntl(<CommunicationsGenerator {...defaultProps} />)

    expect(screen.getByText('Generar comunicación')).toBeDefined()
    expect(screen.getByText('Canal')).toBeDefined()
    expect(screen.getByText('Tono')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Generar borrador' })).toBeDefined()
  })

  it('calls generateCommunication on generate click and shows draft in textarea', async () => {
    mockGenerate.mockResolvedValue(mockDraftResponse)

    renderWithIntl(<CommunicationsGenerator {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Generar borrador' }))

    await vi.waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledOnce()
    })

    expect(mockGenerate).toHaveBeenCalledWith(
      defaultProps.scenarioId,
      defaultProps.clientId,
      { channel: 'email', tone: 'formal' },
    )

    // Draft text should appear in the textarea
    await vi.waitFor(() => {
      expect(
        screen.getByDisplayValue('Estimado cliente, le recordamos su saldo pendiente.'),
      ).toBeDefined()
    })

    // Send button should be present
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDefined()
  })

  it('shows loading state while generating', async () => {
    let resolvePromise: (v: unknown) => void = () => {}
    mockGenerate.mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve
      }),
    )

    renderWithIntl(<CommunicationsGenerator {...defaultProps} />)

    const generateButton = screen.getByRole('button', { name: 'Generar borrador' })
    fireEvent.click(generateButton)

    await vi.waitFor(() => {
      expect((generateButton as HTMLButtonElement).disabled).toBe(true)
    })

    // Resolve
    resolvePromise(mockDraftResponse)
  })

  it('shows inline error on generate failure', async () => {
    mockGenerate.mockRejectedValue(new Error('Error al generar el borrador'))

    renderWithIntl(<CommunicationsGenerator {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Generar borrador' }))

    await vi.waitFor(() => {
      expect(screen.getByText('Error al generar el borrador')).toBeDefined()
    })
  })

  it('calls sendCommunication on send confirmation', async () => {
    mockGenerate.mockResolvedValue(mockDraftResponse)
    mockSend.mockResolvedValue(mockSentResponse)

    renderWithIntl(<CommunicationsGenerator {...defaultProps} />)

    // Generate draft first
    fireEvent.click(screen.getByRole('button', { name: 'Generar borrador' }))
    await vi.waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledOnce()
    })

    // Wait for Send button to appear after state update
    const sendButton = await screen.findByRole('button', { name: 'Enviar' })
    fireEvent.click(sendButton)

    await vi.waitFor(() => {
      expect(mockSend).toHaveBeenCalledOnce()
    })

    expect(mockSend).toHaveBeenCalledWith(
      defaultProps.scenarioId,
      defaultProps.clientId,
      'comm-001',
    )
  })

  it('shows success message after send', async () => {
    mockGenerate.mockResolvedValue(mockDraftResponse)
    mockSend.mockResolvedValue(mockSentResponse)

    renderWithIntl(<CommunicationsGenerator {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Generar borrador' }))
    await vi.waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledOnce()
    })

    const sendButton = await screen.findByRole('button', { name: 'Enviar' })
    fireEvent.click(sendButton)

    await vi.waitFor(() => {
      expect(screen.getByText('Comunicación enviada exitosamente')).toBeDefined()
    })
  })

  it('does not send when user cancels confirmation', async () => {
    mockGenerate.mockResolvedValue(mockDraftResponse)
    vi.stubGlobal('confirm', vi.fn(() => false))

    renderWithIntl(<CommunicationsGenerator {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Generar borrador' }))
    await vi.waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledOnce()
    })

    const sendButton = await screen.findByRole('button', { name: 'Enviar' })
    fireEvent.click(sendButton)

    // confirm was called but returned false, so sendCommunication should NOT be called
    expect(mockSend).not.toHaveBeenCalled()
  })

  it('shows error on send failure', async () => {
    mockGenerate.mockResolvedValue(mockDraftResponse)
    mockSend.mockRejectedValue(new Error('Error al enviar la comunicación'))

    renderWithIntl(<CommunicationsGenerator {...defaultProps} />)

    fireEvent.click(screen.getByRole('button', { name: 'Generar borrador' }))
    await vi.waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledOnce()
    })

    const sendButton = await screen.findByRole('button', { name: 'Enviar' })
    fireEvent.click(sendButton)

    await vi.waitFor(() => {
      expect(screen.getByText('Error al enviar la comunicación')).toBeDefined()
    })
  })
})