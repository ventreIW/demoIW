import { describe, it, expect, beforeAll } from 'vitest'
import fs from 'fs'
import path from 'path'

interface ManifestIcon {
  src: string
  sizes: string
  type: string
  purpose?: string
}

interface Manifest {
  id: string
  name: string
  short_name: string
  description: string
  start_url: string
  scope: string
  display: string
  orientation: string
  lang: string
  dir: string
  categories: string[]
  background_color: string
  theme_color: string
  icons: ManifestIcon[]
}

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/
const PLACEHOLDER_RE = /wastewater|aguas residuales/i

describe('manifest.json', () => {
  let manifest: Manifest

  beforeAll(() => {
    const manifestPath = path.resolve(__dirname, '../../../public/manifest.json')
    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8')) as Manifest
  })

  describe('identity', () => {
    it.each(['id', 'name', 'short_name', 'description'] as const)(
      'has a non-empty string %s',
      (field) => {
        expect(typeof manifest[field]).toBe('string')
        expect(manifest[field]).toBeTruthy()
      },
    )

    it('describes the collections domain, not the scaffolding placeholder', () => {
      expect(manifest.description).not.toMatch(PLACEHOLDER_RE)
      expect(manifest.name).not.toMatch(PLACEHOLDER_RE)
    })

    it('declares an id so the install target is stable across start_url changes', () => {
      expect(manifest.id).toBe('/')
    })

    it('declares lang and dir', () => {
      expect(manifest.lang).toBe('es')
      expect(manifest.dir).toBe('ltr')
    })

    it('declares at least one category', () => {
      expect(Array.isArray(manifest.categories)).toBe(true)
      expect(manifest.categories.length).toBeGreaterThan(0)
    })
  })

  describe('installability', () => {
    it('has start_url and scope set to "/"', () => {
      expect(manifest.start_url).toBe('/')
      expect(manifest.scope).toBe('/')
    })

    it('has display set to "standalone"', () => {
      expect(manifest.display).toBe('standalone')
    })

    it('declares a portrait orientation', () => {
      expect(manifest.orientation).toBe('portrait')
    })

    it.each(['background_color', 'theme_color'] as const)('has valid hex %s', (field) => {
      expect(manifest[field]).toMatch(HEX_COLOR_RE)
    })
  })

  describe('icons', () => {
    it('provides both 192x192 and 512x512 entries', () => {
      expect(Array.isArray(manifest.icons)).toBe(true)
      const sizes = manifest.icons.map((icon) => icon.sizes)
      expect(sizes).toContain('192x192')
      expect(sizes).toContain('512x512')
    })

    it('declares a maskable icon so Android does not letterbox the adaptive icon', () => {
      const maskable = manifest.icons.filter((icon) => icon.purpose?.includes('maskable'))
      expect(maskable.length).toBeGreaterThan(0)
      expect(maskable.some((icon) => icon.sizes === '512x512')).toBe(true)
    })

    it('gives every icon a src, sizes, type and purpose', () => {
      for (const icon of manifest.icons) {
        expect(icon.src).toMatch(/^\/icons\//)
        expect(icon.sizes).toMatch(/^\d+x\d+$/)
        expect(icon.type).toBe('image/png')
        expect(icon.purpose).toBeTruthy()
      }
    })

    it('points every icon src at a file that exists on disk', () => {
      for (const icon of manifest.icons) {
        const iconPath = path.resolve(__dirname, '../../../public', icon.src.replace(/^\//, ''))
        expect(fs.existsSync(iconPath), `${icon.src} is missing`).toBe(true)
      }
    })

    it('ships an apple-touch-icon for iOS home-screen installs', () => {
      const applePath = path.resolve(__dirname, '../../../public/icons/apple-touch-icon.png')
      expect(fs.existsSync(applePath)).toBe(true)
    })
  })
})
