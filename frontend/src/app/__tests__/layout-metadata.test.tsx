import { describe, it, expect, vi } from 'vitest'
import type { Metadata, Viewport } from 'next'
import esMessages from '../../../messages/es.json'
import enMessages from '../../../messages/en.json'

// Under vitest, `next-intl/server` resolves to next-intl's react-client build,
// whose getTranslations throws "not supported in Client Components". The mock
// reads the real catalogs, so the assertions below still verify that
// generateMetadata pulls the right key from the right locale — only the
// server-context plumbing is stubbed. Traverses dotted paths, since a mock that
// only handles top-level keys silently returns the key itself for nested ones.
vi.mock('next-intl/server', () => ({
  getTranslations: async ({ locale, namespace }: { locale: string; namespace: string }) => {
    const catalogs: Record<string, typeof esMessages> = { es: esMessages, en: enMessages }
    const messages = catalogs[locale] ?? esMessages
    const scope = namespace
      .split('.')
      .reduce<unknown>((node, key) => (node as Record<string, unknown>)?.[key], messages)
    return (key: string) =>
      (key
        .split('.')
        .reduce<unknown>((node, part) => (node as Record<string, unknown>)?.[part], scope) ??
        key) as string
  },
  getMessages: async () => esMessages,
  setRequestLocale: () => undefined,
}))

const { generateMetadata, viewport } = await import('../[locale]/layout')

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/
const PLACEHOLDER_RE = /wastewater|aguas residuales/i

function metadataFor(locale: string): Promise<Metadata> {
  return generateMetadata({ params: Promise.resolve({ locale }) })
}

describe('viewport export', () => {
  it('carries themeColor, which Next 15 no longer accepts on metadata', () => {
    expect(viewport.themeColor).toMatch(HEX_COLOR_RE)
  })

  it('sets a responsive viewport so the installed app scales on a phone', () => {
    expect(viewport.width).toBe('device-width')
    expect(viewport.initialScale).toBe(1)
  })

  it('is assignable to the Next.js Viewport type', () => {
    const check: Viewport = viewport
    expect(check).toBe(viewport)
  })
})

describe('generateMetadata', () => {
  it('does not leave themeColor on the metadata export', async () => {
    expect('themeColor' in (await metadataFor('es'))).toBe(false)
  })

  it('links the manifest', async () => {
    expect((await metadataFor('es')).manifest).toBe('/manifest.json')
  })

  it.each([
    ['es', esMessages.app.description],
    ['en', enMessages.app.description],
  ])('resolves the %s description from the catalog', async (locale, expected) => {
    expect((await metadataFor(locale)).description).toBe(expected)
  })

  it.each(['es', 'en'])('does not describe wastewater treatment in %s', async (locale) => {
    const metadata = await metadataFor(locale)
    expect(metadata.description).not.toMatch(PLACEHOLDER_RE)
    expect(String(metadata.title)).not.toMatch(PLACEHOLDER_RE)
  })

  it('gives the two locales different descriptions', async () => {
    const [es, en] = await Promise.all([metadataFor('es'), metadataFor('en')])
    expect(es.description).not.toBe(en.description)
  })

  it('retains the app title', async () => {
    expect((await metadataFor('es')).title).toBe('demoIW')
  })

  describe('iOS installability', () => {
    it('declares the app as web-app capable with a title', async () => {
      const appleWebApp = (await metadataFor('es')).appleWebApp
      expect(appleWebApp).toMatchObject({
        capable: true,
        statusBarStyle: 'default',
        title: 'demoIW',
      })
    })

    it('points at an apple-touch-icon so the home screen is not a page screenshot', async () => {
      const icons = (await metadataFor('es')).icons as { apple?: string; icon?: string }
      expect(icons.apple).toBe('/icons/apple-touch-icon.png')
      expect(icons.icon).toBe('/icons/icon-192.png')
    })
  })
})
