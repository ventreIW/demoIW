# B-15 i18n Setup — Scope

## In Scope

- Install and configure `next-intl` for Next.js 15 App Router
- Create `src/i18n.ts` with request config (locales: es, en; default: es)
- Create `src/middleware.ts` (or extend existing) for locale detection via `accept-language`
- Create message files: `messages/es.json` and `messages/en.json`
- Wrap `RootLayout` with `NextIntlClientProvider`
- Replace all hardcoded Spanish strings in `MainLayout.tsx` with `useTranslations()`
- Replace all hardcoded Spanish strings in `ScenarioCard.tsx` with `useTranslations()`
- Replace all hardcoded Spanish strings in `CsvUpload.tsx` with `useTranslations()`
- Replace hardcoded metadata strings in `layout.tsx` with `getTranslations()`
- Add sector name translations (manufacturing, retail, professional_services)
- ICU pluralization for client count
- Update `next.config` if needed for next-intl plugin
- Add `en` messages with proper English equivalents
- TypeScript strict — all translation keys typed

## Out of Scope

- Backend i18n (FastAPI — all backend endpoints return structured data, no UI strings)
- Locale switcher UI component (user-facing language toggle)
- RTL support
- More than 2 locales (es, en)
- i18n for PWA manifest or service worker strings
- Content translation of scenario data / names (user-generated content)
- next-intl rich text or markdown messages
- Locale-specific number/date formatting (beyond what next-intl provides by default)

## Done when

- [ ] `next-intl` installed and configured
- [ ] Middleware handles locale detection and redirects
- [ ] All 18+ hardcoded Spanish strings replaced with translation keys
- [ ] `es.json` contains all Spanish translations
- [ ] `en.json` contains all English translations
- [ ] App renders correctly in Spanish (/) and English (/en)
- [ ] `html lang` attribute reflects active locale
- [ ] Existing tests pass without modification (strings should match es defaults)
- [ ] New i18n config test: middleware test for locale detection
- [ ] TypeScript compiles with `tsc --noEmit`