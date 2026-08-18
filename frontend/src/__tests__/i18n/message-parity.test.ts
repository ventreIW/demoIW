import { describe, it, expect } from 'vitest'
import esMessages from '../../../messages/es.json'
import enMessages from '../../../messages/en.json'

type Catalog = Record<string, unknown>

function flatten(node: Catalog, prefix = ''): Record<string, string> {
  const flat: Record<string, string> = {}
  for (const [key, value] of Object.entries(node)) {
    const path = prefix ? `${prefix}.${key}` : key
    if (value !== null && typeof value === 'object') {
      Object.assign(flat, flatten(value as Catalog, path))
    } else {
      flat[path] = String(value)
    }
  }
  return flat
}

const es = flatten(esMessages as Catalog)
const en = flatten(enMessages as Catalog)

/**
 * Keys whose value is legitimately identical in Spanish and English — proper
 * nouns, symbols, units, and ES/EN cognates. Each was reviewed individually.
 *
 * The point of the allowlist is that it must be edited deliberately: a *new*
 * key with the same value in both catalogs is an untranslated string and fails
 * the guard below. Adding an entry here is a claim that the word really is the
 * same in both languages.
 */
const IDENTICAL_VALUE_ALLOWLIST = new Set([
  'app.title', // product name
  'scenarioForm.sector', // cognate
  'scenarioForm.seedPlaceholder', // "Auto" — cognate
  'scenarioForm.sectors.retail', // "Retail" — used as-is in ES
  'scenarioForm.results.sector', // cognate
  'scenarioForm.results.id', // "ID:" — symbol
  'casesPage.columnRank', // "#" — symbol
  'casesPage.columnScore', // "Score" — used as-is in ES
  'casesPage.daysUnit', // "{days} d" — unit abbreviation
  'caseDetail.sectionScore', // "Score"
  'caseDetail.sector', // cognate
  'caseDetail.folio', // domain term, used as-is in both
  'communications.channels.whatsapp', // proper noun
  'communications.tones.formal', // cognate
  'executivePage.query.total', // cognate
])

const PLACEHOLDER_RE = /wastewater|aguas residuales/i

describe('message catalog parity', () => {
  it('has the same key set in both locales', () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(es).sort())
  })

  it('has no empty values', () => {
    for (const [locale, catalog] of [
      ['es', es],
      ['en', en],
    ] as const) {
      for (const [key, value] of Object.entries(catalog)) {
        expect(value.trim(), `${locale}.${key} is empty`).not.toBe('')
      }
    }
  })

  /**
   * The leak s7.3's parity check could not see. Key parity held because the
   * placeholder description was present in *both* catalogs with the same
   * English value — matching key sets, untranslated copy.
   */
  it('has no key carrying an identical value in both locales', () => {
    const identical = Object.keys(es).filter(
      (key) => es[key] === en[key] && !IDENTICAL_VALUE_ALLOWLIST.has(key),
    )
    expect(
      identical,
      'Untranslated key(s). Translate them, or add to IDENTICAL_VALUE_ALLOWLIST ' +
        'if the word really is the same in both languages.',
    ).toEqual([])
  })

  it('carries no scaffolding placeholder copy', () => {
    const offending = [...Object.entries(es), ...Object.entries(en)]
      .filter(([, value]) => PLACEHOLDER_RE.test(value))
      .map(([key]) => key)
    expect(offending).toEqual([])
  })

  it('provides the offline fallback copy the service worker precaches', () => {
    for (const key of ['offline.title', 'offline.body', 'offline.retry']) {
      expect(Object.keys(es)).toContain(key)
      expect(Object.keys(en)).toContain(key)
    }
  })

  it('provides the home page copy', () => {
    for (const key of ['app.homeTitle', 'app.homeSubtitle']) {
      expect(Object.keys(es)).toContain(key)
      expect(Object.keys(en)).toContain(key)
    }
  })
})
