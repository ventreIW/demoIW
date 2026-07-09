# B-15 i18n Setup — Implementation Plan

**Story:** B-15 | **Size:** S | **Date:** 2026-07-08
**Design:** [b15-design.md](./b15-design.md)

## Pre-Implementation Decisions

These open questions from design need resolution before specific tasks:

1. **Sector labels in English:** Display raw keys (`manufacturing`) or proper nouns (`Manufacturing`)? 
   → Resolve in Task 3 (string replacement). Default: proper nouns for English (`Manufacturing`, `Retail`, `Professional Services`), raw keys for Spanish (same as current).
2. **Metadata translation:** Static or per-locale?
   → Resolve in Task 2 (layout). Default: static metadata (same title/description for both locales) — simpler, and the description is technical.

## Tasks

### Task 1: Install next-intl + create config scaffolding [S, no deps]

**What:** Add the dependency and create all config/message files. No existing code changes — just new files that nothing imports yet. This establishes the foundation before the structural changes in Task 2.

**Files:**
- modify: `frontend/package.json` — add `next-intl`
- create: `frontend/src/i18n.ts` — `getRequestConfig({ locales: ['es', 'en'], defaultLocale: 'es' })`
- create: `frontend/src/i18n/routing.ts` — `defineRouting({ locales: ['es', 'en'], defaultLocale: 'es', localePrefix: 'as-needed' })`
- create: `frontend/src/messages/es.json` — all 18+ Spanish translations
- create: `frontend/src/messages/en.json` — all 18+ English translations

**AC reference:** All scenarios (AC1-AC6 from story.md)

**Verification:**
| Gate | Command |
|------|---------|
| Types | `rai gate check gate-types` |
| Lint | `rai gate check gate-lint` |

**TDD:** No component changes yet — config-only. Verify JSON files are valid and TypeScript compiles with the new import types.

---

### Task 2: Restructure to [locale] routing + test wrapper [M, depends on T1]

**What:** Wire next-intl into the Next.js middleware and [locale] segment. Move all pages from `src/app/` to `src/app/[locale]/`. Create test wrapper so existing tests work with NextIntlClientProvider. This is the structural heart of the change — after this, the app routes through locale-aware middleware and components have access to translations (though they still use hardcoded strings).

**Files:**
- modify: `frontend/src/middleware.ts` — wrap with `createMiddleware` from next-intl, preserve scenario redirect
- create: `frontend/src/app/[locale]/layout.tsx` — real layout with `NextIntlClientProvider`, locale-aware metadata
- modify: `frontend/src/app/layout.tsx` — thin pass-through (or delete if next-intl handles it)
- create: `frontend/src/app/[locale]/page.tsx` — moved from `src/app/page.tsx`
- create: `frontend/src/app/[locale]/scenarios/page.tsx` — moved from `src/app/scenarios/page.tsx`
- create: `frontend/src/app/[locale]/scenarios/CsvUploadWrapper.tsx` — moved
- create: `frontend/src/test-utils/i18n.tsx` — `renderWithIntl` wrapper
- modify: `frontend/vitest.config.ts` — add `setupFiles: []` or alias
- modify: `frontend/src/components/scenarios/__tests__/ScenarioCard.test.tsx` — use `renderWithIntl`
- modify: `frontend/src/components/scenarios/__tests__/CsvUpload.test.tsx` — use `renderWithIntl`
- modify: `frontend/src/app/__tests__/layout-metadata.test.tsx` — use `renderWithIntl` or adjust for [locale]

**AC reference:** AC1 (es default), AC2 (en locale), AC3 (html lang)

**Verification:**
| Gate | Command |
|------|---------|
| Tests | `rai gate check gate-tests` |
| Types | `rai gate check gate-types` |
| Lint | `rai gate check gate-lint` |

**TDD cycle:**
1. RED: Move pages to `[locale]/` → existing tests break (no NextIntlClientProvider in render tree)
2. GREEN: Add `renderWithIntl` wrapper → update tests to use it → all tests pass
3. REFACTOR: Clean up imports, verify middleware preserves scenario redirect

---

### Task 3: Replace hardcoded strings with translation keys [M, depends on T2]

**What:** Replace every hardcoded Spanish string in client components with `useTranslations()` calls. Add ICU pluralization for client count. Translate sector labels in English. This is the content layer — after this, the app is fully i18n'd.

**Files:**
- modify: `frontend/src/components/layout/MainLayout.tsx` — sidebar labels via `t('sidebar.*')`
- modify: `frontend/src/components/scenarios/ScenarioCard.tsx` — status, sector, actions, client count via `t('scenario.*')`
- modify: `frontend/src/components/scenarios/CsvUpload.tsx` — buttons, messages via `t('csv.*')`
- modify: `frontend/src/app/[locale]/layout.tsx` — metadata via `getTranslations()` (if async) or keep static

**AC reference:** AC1-AC6, SHOULD AC1 (pluralization)

**Verification:**
| Gate | Command |
|------|---------|
| Tests | `rai gate check gate-tests` |
| Types | `rai gate check gate-types` |
| Lint | `rai gate check gate-lint` |
| Format | `rai gate check gate-format` |

**TDD cycle:**
1. RED: Tests should still be GREEN from T2 — string assertions match Spanish defaults. If any test breaks, the translation key is wrong.
2. GREEN: Replace one component at a time, run tests after each to confirm Spanish strings still match.
3. REFACTOR: Clean up unused imports, remove hardcoded `SECTOR_LABELS` map.

**Manual smoke test:** `cd frontend && npm run dev`, then:
- Visit `/` → verify sidebar, scenario cards, CSV upload all in Spanish
- Visit `/en` → verify same components in English
- Verify `html lang="es"` and `html lang="en"` respectively
- Verify scenario redirect still works (no cookie → redirect to `/scenarios`)

---

## Gate Policy

| When | Command | Scope |
|------|---------|-------|
| Per task | `rai gate check gate-tests` | Full (frontend + backend — scripts run both, backend tests are fast) |
| Per task | `rai gate check gate-lint` | Full project |
| Per task | `rai gate check gate-format` | Full project |
| Per task | `rai gate check gate-types` | Full project |
| End of story | Manual smoke test | `npm run dev`, verify `/` and `/en` |
| MR creation | `/rai-mr-create` | Full suite |

## Execution Order

```
T1 (config) ──→ T2 (routing + tests) ──→ T3 (strings)
```

Sequential — each builds on the previous. No parallelization possible (T2 needs T1's config, T3 needs T2's routing).

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| [locale] restructure breaks existing URL patterns | Middleware rewrites handle legacy routes; `localePrefix: 'as-needed'` preserves `/scenarios` for default locale |
| Tests require NextIntlClientProvider but vitest doesn't auto-load it | Task 2 creates `renderWithIntl` wrapper, applied to all affected test files |
| next-intl version compatibility with Next.js 15.3 | Pin to latest next-intl; Next.js 15 App Router is fully supported |
| Middleware ordering: i18n vs scenario redirect | i18n middleware runs first (locale detection), then scenario guard runs on the resolved path |

## Duration Tracking

| Task | Planned | Actual | Notes |
|------|---------|--------|-------|
| T1: Config scaffolding | S | — | |
| T2: Routing + tests | M | — | |
| T3: String replacement | M | — | |
| **Total** | **~1h** | — | |