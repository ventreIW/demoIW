---
epic_id: "E9"
title: "i18n with next-intl"
status: "draft"
created: "2026-07-13"
---

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