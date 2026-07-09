import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

interface ManifestIcon {
  src: string
  sizes: string
  type: string
}

interface Manifest {
  name: string
  short_name: string
  description: string
  start_url: string
  display: string
  background_color: string
  theme_color: string
  icons: ManifestIcon[]
}

const HEX_COLOR_RE = /^#[0-9a-fA-F]{6}$/

describe('manifest.json', () => {
  let manifest: Manifest

  beforeAll(() => {
    const manifestPath = path.resolve(__dirname, '../../../../frontend/public/manifest.json')
    const raw = fs.readFileSync(manifestPath, 'utf-8')
    manifest = JSON.parse(raw) as Manifest
  })

  it('has a non-empty name', () => {
    expect(manifest.name).toBeTruthy()
    expect(typeof manifest.name).toBe('string')
  })

  it('has a non-empty short_name', () => {
    expect(manifest.short_name).toBeTruthy()
    expect(typeof manifest.short_name).toBe('string')
  })

  it('has a non-empty description', () => {
    expect(manifest.description).toBeTruthy()
    expect(typeof manifest.description).toBe('string')
  })

  it('has start_url set to "/"', () => {
    expect(manifest.start_url).toBe('/')
  })

  it('has display set to "standalone"', () => {
    expect(manifest.display).toBe('standalone')
  })

  it('has valid hex background_color', () => {
    expect(manifest.background_color).toMatch(HEX_COLOR_RE)
  })

  it('has valid hex theme_color', () => {
    expect(manifest.theme_color).toMatch(HEX_COLOR_RE)
  })

  it('has icons array with 192x192 and 512x512 entries', () => {
    expect(Array.isArray(manifest.icons)).toBe(true)
    expect(manifest.icons.length).toBeGreaterThanOrEqual(2)

    const sizes = manifest.icons.map((icon) => icon.sizes)
    expect(sizes).toContain('192x192')
    expect(sizes).toContain('512x512')
  })

  it('each icon has src, sizes, and type fields', () => {
    for (const icon of manifest.icons) {
      expect(icon.src).toBeTruthy()
      expect(icon.sizes).toBeTruthy()
      expect(icon.type).toBe('image/png')
    }
  })
})