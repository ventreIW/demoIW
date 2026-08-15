import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * T1 — Design token / focus foundation test (a11y root cause).
 *
 * The UI primitives (button/input/select) reference Tailwind tokens (`bg-primary`,
 * `text-primary-foreground`, `ring-ring/50`, `border-ring`, `bg-muted`, ...). Before
 * this story those tokens were never defined (empty theme.extend + no CSS vars), so the
 * generated classes resolved to nothing — primary buttons rendered transparent and focus
 * rings were invisible. This test locks the fix: tokens must be defined in globals.css
 * and wired into tailwind.config.ts, plus a global focus-visible fallback.
 *
 * It reads the actual source files (not a mock) so it fails loudly if the config is ever
 * reverted to the empty state.
 */

const ROOT = process.cwd() // vitest runs from frontend/
const tailwindPath = resolve(ROOT, 'tailwind.config.ts')
const globalsPath = resolve(ROOT, 'src', 'styles', 'globals.css')

function readTailwindConfig(): string {
  return readFileSync(tailwindPath, 'utf-8')
}

function readGlobals(): string {
  return readFileSync(globalsPath, 'utf-8')
}

describe('design tokens + focus foundation (a11y root cause)', () => {
  it('tailwind config wires every token used by the UI primitives', () => {
    const cfg = readTailwindConfig()
    for (const token of [
      'background',
      'foreground',
      'primary',
      'primary-foreground',
      'muted',
      'muted-foreground',
      'ring',
      'border',
      'input',
      'destructive',
    ]) {
      // token may be keyed with or without quotes in the config source
      expect(cfg).toMatch(new RegExp(`['"]?${token}['"]?\\s*:`))
    }
  })

  it('globals.css declares the corresponding :root CSS variables', () => {
    const css = readGlobals()
    for (const varName of [
      '--background',
      '--foreground',
      '--primary',
      '--primary-foreground',
      '--muted',
      '--muted-foreground',
      '--ring',
      '--border',
      '--input',
      '--destructive',
    ]) {
      expect(css).toContain(varName)
    }
  })

  it('globals.css provides a global focus-visible fallback', () => {
    const css = readGlobals()
    expect(css).toMatch(/\*:focus-visible|:focus-visible/)
  })
})
