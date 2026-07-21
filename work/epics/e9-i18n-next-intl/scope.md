# Epic Scope: i18n with next-intl

> ⛔ **SUPERSEDED 2026-07-20 — do not plan from this file.** The work below was already
> delivered by `work/backlog/b15-i18n-setup` (merged 2026-07-08). The only unbuilt item is the
> language switcher (B-18), now tracked as **E4 s4.7** together with the untranslated
> `GenerateScenarioForm.tsx`. Stories B-16/B-17/B-19 target pages and components that either
> do not exist or were translated by `b15`. See `brief.md` for the full account.

## Objective
Implement internationalization (i18n) in the demoIW application using the next-intl library to support English and Spanish languages, with a language switcher and proper routing.

## In Scope
- Install and configure next-intl
- Create translation files for Spanish (es.json) and English (en.json)
- Replace hardcoded strings with translation keys throughout the frontend
- Implement a language switcher component (dropdown or toggle)
- Configure routing to support locale prefixes (e.g., /en/about) while keeping Spanish as the default without prefix
- Ensure all pages and components are translated
- Write unit tests for translation components
- Update documentation to reflect the i18n feature

## Out of Scope
- Translating backend error messages or logs
- Supporting right-to-left (RTL) layouts
- Adding more than two languages (English and Spanish) in this epic
- Implementing user-specific language preferences stored in a database (browser-only storage for now)
- Automatic language detection based on geolocation (we will use browser navigator.language)

## Planned Stories
- B-15: i18n Setup (next-intl) - initial setup, translation files, basic translation of a few components
- B-16: Translate Core Components (header, footer, main navigation)
- B-17: Translate Home Page and About Page
- B-18: Language Switcher Component and Route Integration
- B-19: Translate Remaining Pages (Dashboard, Settings, etc.)
- B-20: Testing and Quality Assurance (unit tests, e2e tests for language switching)

## Done Criteria
- All user-facing text in the frontend is wrapped with next-intl translation hooks
- Both Spanish and English translations are complete for all pages and components
- Language switcher appears in the header and correctly changes the language
- URLs reflect the locale (no prefix for Spanish, /en for English)
- The application builds and runs without errors in both languages
- Automated tests (unit and e2e) pass for the i18n functionality
- Documentation updated in the README or a separate i18n guide