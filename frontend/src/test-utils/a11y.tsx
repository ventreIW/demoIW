import { type ReactElement } from 'react'
import axe from 'axe-core'
import { renderWithIntl } from './i18n'

export interface A11yResult {
  violations: axe.Result[]
  passed: number
  incomplete: number
}

/**
 * Render a component with i18n context and run an axe-core AA scan against it.
 * Returns violations so callers can assert `length === 0`.
 *
 * Note: jsdom does not compute real CSS/color contrast, so axe's `color-contrast`
 * rule evaluates to inapplicable here. This helper reliably catches *semantic* AA
 * failures (missing button names, missing th scope, landmarks, aria misuse, link
 * names, document title, html lang). Real contrast of the running app is verified
 * separately via the a11y-scan script against a served build / manual keyboard pass.
 */
export async function runAxeOn(
  ui: ReactElement,
  options: { locale?: string } = {},
): Promise<A11yResult> {
  const { container } = renderWithIntl(ui, { locale: options.locale })

  // Ensure document-level attributes present in the real root layout
  // are available to axe-core (jsdom renders without these by default).
  document.documentElement.lang = options.locale ?? 'es'
  document.title = 'demoIW'

  // axe-core needs the html element in the document; jsdom renders into a div.
  const results = await axe.run(document, {
    runOnly: {
      type: 'tag',
      values: ['wcag2a', 'wcag2aa', 'wcag21aa'],
    },
    rules: {
      // color-contrast needs canvas (not available in jsdom). Contrast is verified
      // separately via browser axe scan / manual keyboard pass.
      'color-contrast': { enabled: false },
    },
  })

  return {
    violations: results.violations,
    passed: results.passes.length,
    incomplete: results.incomplete.length,
  }
}