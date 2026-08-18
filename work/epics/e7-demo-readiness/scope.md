# E7 — Demo Readiness scope

**Status:** In progress (s7.1, s7.2, s7.3 completed — s7.4 remaining)

## Stories

| ID | Title | Status | Notes |
|----|-------|--------|-------|
| s7.1 | PWA configuration | **done** ✓ | Hardened hand-rolled SW (ADR-010, no next-pwa): versioned precache, stale-cache cleanup, locale-aware /offline fallback, SWR statics. Manifest completed (id/scope/lang/maskable). Next 15 viewport export; bilingual generateMetadata; iOS apple-touch-icon. E1 wastewater placeholder identity removed |
| s7.2 | Accessibility pass | **done** ✓ | WCAG 2.1 AA contrast audit + fixes; keyboard nav across all panels; axe-core scan (0 violations) |
| s7.3 | English translation pass | **done** ✓ | 172/172 EN keys reviewed; identical-value leak later caught and guarded in s7.1 || s7.4 | End-to-end demo flow validation | pending | Automated smoke test of the full <10-minute demo path (B-16, NFR-01) |

## Open blockers

- ⛔ **`npm run build` fails** on 11 pre-existing ESLint errors (8 parked from s6.2, 3 added by
  s7.2). Confirmed on `main` at `2fc1501`, independent of s7.1. The demo-readiness epic has no
  working production build. Found during s7.1 T5 — see `stories/s7.1-progress.md`.
- Real-Postgres E2E (E6 M4) still open — no Docker on the current host.
