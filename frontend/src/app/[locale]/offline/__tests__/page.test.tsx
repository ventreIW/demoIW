import { screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import esMessages from '../../../../../messages/es.json'
import enMessages from '../../../../../messages/en.json'
import OfflinePage from '../page'

describe('offline fallback page', () => {
  it.each([
    ['es', esMessages],
    ['en', enMessages],
  ])('renders the %s copy the service worker falls back to', (locale, messages) => {
    renderWithIntl(<OfflinePage />, { locale })

    expect(screen.getByRole('heading', { name: messages.offline.title })).toBeDefined()
    expect(screen.getByText(messages.offline.body)).toBeDefined()
  })

  it('offers a retry affordance', () => {
    renderWithIntl(<OfflinePage />, { locale: 'es' })

    const retry = screen.getByRole('button', { name: esMessages.offline.retry })
    expect(retry).toBeDefined()
  })

  it('is a static page with no data dependency, so it can be precached', () => {
    // Rendering without any API mock must not throw — the worker serves this
    // page precisely when the network is gone.
    expect(() => renderWithIntl(<OfflinePage />, { locale: 'en' })).not.toThrow()
  })
})
