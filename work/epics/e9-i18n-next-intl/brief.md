---
epic_id: "E9"
title: "i18n with next-intl"
status: "superseded"
created: "2026-07-13"
superseded: "2026-07-20"
superseded_by: "b15-i18n-setup (delivered), E4 s4.7 (remaining work)"
---

> # ⛔ SUPERSEDED — do not activate
>
> **Retired 2026-07-20.** This epic was planned on 2026-07-13, five days *after* the work it
> describes had already shipped.
>
> **What happened:** `work/backlog/b15-i18n-setup` delivered next-intl v4, `[locale]` routing,
> middleware locale detection, `messages/{es,en}.json`, ICU pluralization and dynamic `html lang`
> — merged **2026-07-08**. That is this epic's story B-15, and it also covers B-16, B-17 and B-19,
> because the components they name were all converted at the same time.
>
> **This brief was written without reading the codebase.** Its stories plan to translate an
> *About page*, a *Dashboard* and a *Settings page*. None of those exist. The application has
> exactly two pages, `/` and `/scenarios`, and both were already translated when this was written.
>
> **The one legitimate story was B-18 (language switcher)**, which `b15` explicitly scoped out and
> nobody built. That work, plus a regression in `GenerateScenarioForm.tsx`, now lives at
> **E4 s4.7**.
>
> **Why this is kept rather than deleted:** the same work was planned three times — here, as
> E4 s4.1, and as backlog item b15 — because `b15` was tracked in `work/backlog/`, *outside*
> the epic system, so epic planning never saw it. This file is the evidence for fixing that
> split. See `dev/parking-lot.md`.

# Epic Brief: i18n with next-intl

## Hypothesis
For users of the demoIW application who need to use the system in their preferred language (English or Spanish),
providing internationalization with next-intl is a frontend enhancement
that improves accessibility and user experience.
Unlike the current state where all text is hardcoded in Spanish,
our solution will allow dynamic language switching based on user preference or browser locale.

## Success Metrics
- **Leading:** Number of translation keys implemented in the first story
- **Lagging:** Percentage of users who switch language to English (or Spanish if they prefer) after release

## Appetite
M — 5-7 stories

## Scope Boundaries
### In (MUST)
- Implement next-intl library
- Create English translation file (en.json)
- Ensure all UI strings are translated for both Spanish (default) and English
- Add language switcher component
- Ensure URLs reflect locale (no prefix for Spanish, /en for English)
- Maintain SEO and routing integrity

### In (SHOULD)
- Add language detection from user profile (if available)
- Provide a fallback mechanism for missing translations
- Support date and number formatting according to locale

### No-Gos
- Translating backend error messages (out of scope for this epic)
- Supporting right-to-left languages (future epic)

## Rabbit Holes
- Attempting to use a more complex i18n solution (e.g., formatjs) when next-intl suffices
- Over-engineering the language switcher with animations or complex UI