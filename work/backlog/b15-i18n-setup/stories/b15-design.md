# B-15 i18n Setup — Design

## Problem

All UI strings are hardcoded in Spanish. There's no mechanism to render the application in English or any other language. The `html lang="es"` is hardcoded.

## Value

Makes the application accessible to English-speaking users and establishes i18n infrastructure before the codebase grows larger (harder to retrofit later). The i18n pattern becomes the template for all future UI strings.

## Approach

Install `next-intl` (the de facto standard for Next.js App Router i18n), configure locale routing with Spanish as default (no URL prefix), English at `/en/*`, and replace all hardcoded strings with translation keys. This is a mechanical extraction — no new features, no UI changes, no locale switcher.

**Architecture:** next-intl requires the `[locale]` segment in App Router pages. All existing pages move from `src/app/` to `src/app/[locale]/`. The root `src/app/layout.tsx` becomes a thin pass-through (next-intl generates it via `generateStaticParams`). Middleware handles locale detection from `accept-language` header.

**Locale strategy (default locale = no prefix):**
- Spanish (`es`): `/`, `/scenarios`, `/api/...`
- English (`en`): `/en`, `/en/scenarios`, `/en/api/...`
- Middleware setting: `localePrefix: 'as-needed'`

## Components

| File | Change | Purpose |
|------|--------|---------|
| `frontend/package.json` | modify | Add `next-intl` dependency |
| `frontend/src/i18n.ts` | create | `getRequestConfig` — locale list, default locale |
| `frontend/src/messages/es.json` | create | Spanish translations (extracted from current code) |
| `frontend/src/messages/en.json` | create | English translations |
| `frontend/src/i18n/routing.ts` | create | Routing config (locales, defaultLocale, pathnames) |
| `frontend/src/middleware.ts` | modify | Add i18n middleware wrapping existing scenario redirect |
| `frontend/src/app/layout.tsx` | modify | Thin pass-through that generates `[locale]` layout |
| `frontend/src/app/[locale]/layout.tsx` | create | Real layout with `NextIntlClientProvider`, metadata via `getTranslations` |
| `frontend/src/app/[locale]/page.tsx` | create | Moved from `src/app/page.tsx` |
| `frontend/src/app/[locale]/scenarios/page.tsx` | create | Moved from `src/app/scenarios/page.tsx` |
| `frontend/src/app/[locale]/scenarios/CsvUploadWrapper.tsx` | create | Moved from `src/app/scenarios/CsvUploadWrapper.tsx` |
| `frontend/src/components/layout/MainLayout.tsx` | modify | Replace hardcoded strings with `useTranslations()` |
| `frontend/src/components/scenarios/ScenarioCard.tsx` | modify | Replace hardcoded strings with `useTranslations()` |
| `frontend/src/components/scenarios/CsvUpload.tsx` | modify | Replace hardcoded strings with `useTranslations()` |
| `frontend/src/test-utils/i18n.tsx` | create | Test wrapper: `renderWithIntl` providing `NextIntlClientProvider` |
| `frontend/vitest.config.ts` | modify | Add `setupFiles` pointing to test utils |

## Decisions

### D1: next-intl over next-i18next or custom

**Rationale:** `next-intl` is the official recommendation for Next.js App Router internationalization, maintained by the Next.js community. It supports Server Components natively, has ICU message format for pluralization, and is used by Vercel's own templates. `next-i18next` targets Pages Router and doesn't support RSC. Custom solution would reinvent the wheel and miss ecosystem tooling.

### D2: Locale-as-needed (no prefix for default locale)

**Rationale:** Spanish is the primary language (existing codebase default). Adding `/es` prefix would break all existing URLs and bookmarks for no benefit. English gets `/en` prefix. This is the `localePrefix: 'as-needed'` pattern in next-intl. If multiple locales are added later (e.g., Portuguese), only non-default locales get a prefix.

### D3: [locale] segment restructuring

**Rationale:** next-intl v3+ requires `[locale]` in the App Router file hierarchy to support locale-aware routing, metadata, and `generateStaticParams`. The alternative (no `[locale]` segment) only works for single-locale apps and can't route `/en/*` URLs. This is the canonical next-intl App Router pattern.

### D4: Test wrapper over factory function

**Rationale:** A `renderWithIntl` utility wrapping `@testing-library/react`'s `render` with `NextIntlClientProvider` is the minimal change. An alternative would be to mock `useTranslations` globally, but that weakens tests (strings wouldn't be validated against actual message keys). A test wrapper that injects the real `es` messages validates that keys exist and match the expected Spanish strings.

### D5: ICU MessageFormat for pluralization

**Rationale:** `{count} clientes` must handle singular/plural. ICU provides `{count, plural, =1 {1 cliente} other {# clientes}}`. This is natively supported by next-intl via `t('scenario.clientCount', { count: 5 })`.

## Legacy Sweep

Nothing — this is net-new. No V1 i18n mechanism exists to orphan.

## Drift Risks

No `governance/drift-hotspots.json` file. AG4 check: this change touches 6 files across components + routing + testing layers — moderate fan-out but all changes are low-risk (string replacement + wrapper addition). AG2: no clone amplification — this is the first i18n implementation, establishing the pattern.

## Complexity

Simple — mechanical string extraction, 1 library, no algorithms, no external integrations.

## Dependencies

None. No other stories block this, and this blocks no other stories (frontend-only change).

## Acceptance Criteria

### MUST

1. App renders all UI in Spanish when locale is `es` (default) or browser sends `Accept-Language: es`
2. App renders all UI in English when locale is `en` (URL `/en/*`) or browser sends `Accept-Language: en`
3. `html lang` attribute reflects the active locale (`es` or `en`)
4. All existing tests pass — string assertions match Spanish default
5. TypeScript compiles with `tsc --noEmit`
6. Sidebar navigation links are translated in both locales

### SHOULD

1. ICU pluralization works: `0 clientes`, `1 cliente`, `5 clientes` (es) / `0 clients`, `1 client`, `5 clients` (en)
2. Middleware preserves existing scenario redirect behavior (guard for `active_scenario_id` cookie)

### MUST NOT

1. No locale switcher UI component (out of scope)
2. No changes to backend (FastAPI)
3. No changes to API endpoints
4. No translation of user-generated content (scenario names, sector values)
5. No changes to PWA manifest or service worker strings

## Testing Strategy

| Layer | Name | Purpose |
|-------|------|---------|
| Unit | `layout-metadata.test.tsx` | Metadata still returns 'demoIW' (unchanged) |
| Unit | `ScenarioCard.test.tsx` | Renders Spanish strings with default locale |
| Unit | `CsvUpload.test.tsx` | Renders Spanish strings with default locale |
| Unit | `middleware i18n` (new) | Locale detection from accept-language header |
| Integration | Manual smoke test | Visit `/` (Spanish), `/en` (English), verify sidebar, cards, upload button |

## Examples

### Config: `src/i18n.ts`
```typescript
import { getRequestConfig } from 'next-intl/server'

export default getRequestConfig({
  locales: ['es', 'en'],
  defaultLocale: 'es',
})
```

### Routing: `src/i18n/routing.ts`
```typescript
import { defineRouting } from 'next-intl/routing'

export const routing = defineRouting({
  locales: ['es', 'en'],
  defaultLocale: 'es',
  localePrefix: 'as-needed',
})
```

### Spanish messages: `src/messages/es.json` (excerpt)
```json
{
  "sidebar": {
    "operations": "Operaciones",
    "executive": "Ejecutivo",
    "scenarios": "Escenarios"
  },
  "scenario": {
    "status": {
      "active": "Activo",
      "noData": "Sin datos",
      "withData": "Con datos"
    },
    "actions": {
      "select": "Seleccionar",
      "activating": "Activando..."
    },
    "clientCount": "{count, plural, =0 {0 clientes} =1 {1 cliente} other {# clientes}}"
  },
  "csv": {
    "uploadButton": "Subir CSV",
    "upload": "Subir",
    "uploading": "Subiendo...",
    "selectFile": "Seleccionar archivo CSV",
    "cancelSelection": "Cancelar seleccion",
    "errorUpload": "Error al subir el archivo.",
    "successCreated": "Escenario \"{name}\" creado correctamente."
  },
  "sectors": {
    "manufacturing": "manufacturing",
    "retail": "retail",
    "professional_services": "professional_services"
  },
  "app": {
    "title": "demoIW",
    "description": "Industrial wastewater treatment decision support"
  }
}
```

### English messages: `src/messages/en.json` (excerpt)
```json
{
  "sidebar": {
    "operations": "Operations",
    "executive": "Executive",
    "scenarios": "Scenarios"
  },
  "scenario": {
    "status": {
      "active": "Active",
      "noData": "No data",
      "withData": "With data"
    },
    "actions": {
      "select": "Select",
      "activating": "Activating..."
    },
    "clientCount": "{count, plural, =0 {0 clients} =1 {1 client} other {# clients}}"
  },
  "csv": {
    "uploadButton": "Upload CSV",
    "upload": "Upload",
    "uploading": "Uploading...",
    "selectFile": "Select CSV file",
    "cancelSelection": "Cancel selection",
    "errorUpload": "Error uploading file.",
    "successCreated": "Scenario \"{name}\" created successfully."
  },
  "sectors": {
    "manufacturing": "Manufacturing",
    "retail": "Retail",
    "professional_services": "Professional Services"
  },
  "app": {
    "title": "demoIW",
    "description": "Industrial wastewater treatment decision support"
  }
}
```

### Component usage: `ScenarioCard.tsx`
```typescript
'use client'

import { useTranslations } from 'next-intl'

export default function ScenarioCard({...}: ScenarioCardProps) {
  const t = useTranslations()

  // Before: <span>Activo</span>
  // After:
  <span>{t('scenario.status.active')}</span>

  // ICU pluralization:
  // Before: <span>{scenario.client_count} clientes</span>
  // After:
  <span>{t('scenario.clientCount', { count: scenario.client_count })}</span>
}
```

### Test wrapper: `src/test-utils/i18n.tsx`
```typescript
import { ReactNode } from 'react'
import { NextIntlClientProvider } from 'next-intl'
import { render, RenderOptions } from '@testing-library/react'
import esMessages from '@/messages/es.json'

function IntlWrapper({ children }: { children: ReactNode }) {
  return (
    <NextIntlClientProvider locale="es" messages={esMessages}>
      {children}
    </NextIntlClientProvider>
  )
}

export function renderWithIntl(ui: ReactNode, options?: RenderOptions) {
  return render(ui, { wrapper: IntlWrapper, ...options })
}
```

## Open Questions

1. Should sector translation keys be the raw sector values (e.g., `sectors.manufacturing` → "Manufacturing") or should sector values remain as-is and only UI labels be translated? The current code uses sector values as display labels directly — English translations may want to display "Manufacturing" instead of "manufacturing".

2. For metadata (title, description) — these live in `layout.tsx` which is a Server Component. Should we use `getTranslations()` (server-side) or static exports with locale param? `getTranslations()` requires `async` layout — feasible with Next.js 15 but adds complexity to a simple static metadata pattern.