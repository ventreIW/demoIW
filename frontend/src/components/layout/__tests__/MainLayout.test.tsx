import { screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { renderWithIntl } from '@/test-utils/i18n'
import MainLayout from '../MainLayout'

// Both MainLayout and LocaleSwitcher import from @/i18n/routing
const mockReplace = vi.fn()
vi.mock('@/i18n/routing', () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  usePathname: () => '/cases',
}))

describe('MainLayout a11y (T2)', () => {
  it('renders a skip-to-content link as the first focusable element', () => {
    const { container } = renderWithIntl(
      <MainLayout>
        <p>content</p>
      </MainLayout>,
      { locale: 'es' },
    )

    const skipLink = container.querySelector('a[href="#main-content"]')
    expect(skipLink).not.toBeNull()
    // Should be the first element in the container
    expect(container.firstChild?.firstChild).toBe(skipLink)
  })

  it('renders <main> with id="main-content" and an aria-label', () => {
    renderWithIntl(
      <MainLayout>
        <p>content</p>
      </MainLayout>,
      { locale: 'es' },
    )

    const main = document.getElementById('main-content')
    expect(main).not.toBeNull()
    expect(main?.tagName).toBe('MAIN')
    expect(main?.getAttribute('aria-label')).toBeTruthy()
  })

  it('marks the sidebar <nav> as a navigation landmark', () => {
    renderWithIntl(
      <MainLayout>
        <p>content</p>
      </MainLayout>,
      { locale: 'es' },
    )

    const nav = screen.getByRole('navigation')
    expect(nav).toBeDefined()
  })

  it('sets aria-current="page" on the active sidebar link', () => {
    renderWithIntl(
      <MainLayout>
        <p>content</p>
      </MainLayout>,
      { locale: 'es' },
    )

    // With usePathname mocked to '/cases', the operations link should have aria-current
    const operationsLink = screen.getByRole('link', { name: /operaciones/i })
    expect(operationsLink?.getAttribute('aria-current')).toBe('page')
  })
})
