# Retrospective: B-15 — i18n Setup (next-intl)

**Dates:** 2026-07-08 → 2026-07-08
**Estimated:** ~1h | **Actual:** ~1h

## Summary

Installed next-intl v4, configured locale-based routing (es=/default, en=/en), restructured Next.js App Router to `[locale]` segment, replaced all 18+ hardcoded Spanish strings with `useTranslations()`, created test wrapper for vitest. All 33 tests pass, types clean. No regressions.

## What went well

- **Test-first approach held up**: All tests stayed green throughout the [locale] restructuring. The test wrapper pattern (`renderWithIntl`) was clean and reusable — each component test needed just a `render→renderWithIntl` swap.
- **Oldest test caught a miss**: When `ScenarioGrid.test.tsx` failed (3 tests), it was because `ScenarioGrid` renders `ScenarioCard` which uses `useTranslations()` — an indirect dependency the wrapper pattern caught immediately. Error messages were clear.
- **TypeScript was the safety net**: The `next-intl` v4 type system caught the incorrect `locales` prop in `getRequestConfig` immediately. No runtime debugging needed.
- **ICU pluralization worked first try**: Spanish (`1 cliente`/`5 clientes`) and English (`1 client`/`5 clients`) both correct out of the box.

## What to improve

- **API version mismatch between plan and reality**: The design plan assumed next-intl v3 API (`getRequestConfig` with static `locales`/`defaultLocale`). v4 dropped those — they moved to `defineRouting`. This caused a T1 rework. A 30-second check of `node_modules/next-intl/dist/types/` type definitions would have caught this before writing the design.
- **Message file location**: Design placed messages at `src/messages/`; docs place them at project-root `messages/`. The `request.ts` import path depended on this. Caught by type checking the import resolution, but a docs check upfront would have avoided the move.
- **Backlog adapter unavailable**: No Jira integration meant story transitions and learning records weren't automatically tracked. The story lifecycle worked manually but without automation.

## Heutagogical Checkpoint

1. **What did I learn?**
   - next-intl v4 has a fundamentally different file structure from v3: `i18n/request.ts` (not `i18n.ts`), `messages/` at project root, `createMiddleware` from `next-intl/middleware`, `next-intl/plugin` in next.config.ts. The `getRequestConfig` callback receives `{requestLocale}` which must be awaited — it's a Promise.
   - The `[locale]` segment is mandatory for multi-locale App Router routing. All pages live under it. Root layout becomes a pass-through. `html lang` is set dynamically from the locale param in `[locale]/layout.tsx`.
   - Any component tree containing `useTranslations()` needs `NextIntlClientProvider` in tests — even if the component under test doesn't import it directly. The indirect caller (e.g., `ScenarioGrid` renders `ScenarioCard`) still needs the wrapper.

2. **What would I change about the process?**
   - Before writing the design approach, read the installed dependency's type definitions to verify API assumptions. A quick `cat node_modules/next-intl/dist/types/server/react-server/getRequestConfig.d.ts` would have revealed the v4 signature immediately.
   - Gemba walk should include checking the actual dependency README or types, not just searching the codebase.

3. **Framework improvements?**
   - `nextjs-vitest-patterns.md` reference in `rai-story-implement` should include the `renderWithIntl` pattern — it's now a canonical pattern for any project using next-intl.
   - The design skill could include a "verify dependency API" step before writing the approach — especially for new dependencies being introduced.

4. **More capable of now?**
   - Can set up next-intl v4 from scratch in <10 minutes — know the exact file structure, middleware pattern, test wrapper, and ICU pluralization.
   - Can write `renderWithIntl` wrappers for any i18n library that requires provider context.
   - Understand the `[locale]` segment architecture for Next.js App Router i18n.

## Improvements applied

- **PAT-R-2**: next-intl v4 App Router setup pattern persisted — file structure, middleware, plugin, `[locale]` segment.
- **PAT-R-3**: i18n test wrapper pattern (renderWithIntl) — includes pitfall about indirect `useTranslations()` callers.

## Patterns added / reinforced

| Pattern | Vote | Reason |
|---------|:----:|--------|
| PAT-R-2 (next-intl v4 setup) | new | Discovered during T1/T2 implementation |
| PAT-R-3 (i18n test wrapper) | new | Discovered during T2 test updates |
| BASE-049 (Dependency placement) | +1 | next-intl isolated to frontend — no backend leakage |

## Learning chain summary

- **Records found**: 0 (no learning records directory — `backlog: null` in manifest, Jira adapter not configured)
- **Aggregate metrics**: N/A — no automated learning system active
- **Notable gaps**: Backlog adapter absence means no Jira issue tracking for this story. Story transitions happened only in the RaiSE signal database (~/.rai/raise.db).
- **Downstream enrichments**: The two new patterns (PAT-R-2, PAT-R-3) provide concrete, searchable references for future i18n stories in this project.