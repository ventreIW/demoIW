import { describe, it, expect } from 'vitest'
import { metadata } from '../layout'
import type { Metadata } from 'next'

describe('layout metadata', () => {
  it('includes manifest pointing to /manifest.json', () => {
    expect(metadata.manifest).toBe('/manifest.json')
  })

  it('has a non-empty theme color as hex string', () => {
    expect(metadata.themeColor).toBeTruthy()
    expect(metadata.themeColor).toMatch(/^#[0-9a-fA-F]{6}$/)
  })

  it('retains existing title', () => {
    expect(metadata.title).toBe('demoIW')
  })

  it('retains existing description', () => {
    expect(metadata.description).toBe('Industrial wastewater treatment decision support')
  })

  it('metadata type is assignable to Next.js Metadata', () => {
    // TypeScript structural check — if this compiles, types are correct
    const _check: Metadata = metadata
    expect(_check).toBe(metadata)
  })
})