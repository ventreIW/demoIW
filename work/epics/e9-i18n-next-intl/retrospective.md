# Retrospective: E9 — i18n with next-intl

**Closed:** 2026-08-20 · **Stories:** 0 delivered under this epic · **Type:** superseded plan

## What this epic actually was

E9 was planned but never executed. Its `scope.md` carries an explicit banner dated 2026-07-20:

> ⛔ **SUPERSEDED — do not plan from this file.** The work below was already delivered by
> `work/backlog/b15-i18n-setup` (merged 2026-07-08).

The plan was written after the work it describes had already shipped. Its six planned stories
(B-15 through B-20) targeted next-intl setup, translation of core components, pages, a language
switcher, and testing — all of which either existed already or referenced components that do
not exist in this codebase.

## Disposition — every planned story accounted for

| Planned | Disposition |
|---|---|
| B-15 i18n setup (next-intl) | **Delivered** by `b15-i18n-setup`, merged 2026-07-08 |
| B-16 translate core components | **Delivered** by the same branch |
| B-17 translate Home/About pages | **Void** — no About page exists in this product |
| B-18 language switcher | **Delivered** as E4 s4.7 (`LocaleSwitcher`, covered by axe scan in s7.2) |
| B-19 translate remaining pages | **Delivered** across E5/E6, completed by E7 s7.3 |
| B-20 i18n testing/QA | **Delivered** — EN/ES key parity guard added in s7.1; 177/177 parity verified at E7 close |

Nothing planned here remains unbuilt. NFR-03 (multilingual interface) is verified against E7's
close, not against this epic.

## Lesson

An epic plan written from a backlog that was not reconciled against merged work produces six
stories of which two are duplicates, three are already done, and one targets a page that does
not exist. The banner was added promptly when it was noticed, which is the right response — but
the epic then stayed open for a month because "superseded" was recorded in the scope file and
nowhere in the tracking.

**Status: CLOSED — superseded before execution. No outstanding work.**
