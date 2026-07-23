import { screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import LocaleSwitcher from '../LocaleSwitcher'

// Mock next-intl's routing module for useRouter/usePathname
const mockReplace = vi.fn()
vi.mock('@/i18n/routing', () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  usePathname: () => '/scenarios',
}))

describe('LocaleSwitcher', () => {
  it('shows EN when current locale is es', () => {
    renderWithIntl(<LocaleSwitcher />, { locale: 'es' })
    expect(screen.getByText('EN')).toBeDefined()
  })

  it('shows ES when current locale is en', () => {
    renderWithIntl(<LocaleSwitcher />, { locale: 'en' })
    expect(screen.getByText('ES')).toBeDefined()
  })

  it('calls router.replace with next locale on click', () => {
    renderWithIntl(<LocaleSwitcher />, { locale: 'es' })
    screen.getByText('EN').click()
    expect(mockReplace).toHaveBeenCalledWith('/scenarios', { locale: 'en' })
  })
})