# E7 — Demo Readiness scope

**Status:** All four stories complete (s7.1–s7.4) — epic close pending

## Stories

| ID | Title | Status | Notes |
|----|-------|--------|-------|
| s7.1 | PWA configuration | **done** ✓ | Hardened hand-rolled SW (ADR-010, no next-pwa): versioned precache, stale-cache cleanup, locale-aware /offline fallback, SWR statics. Manifest completed (id/scope/lang/maskable). Next 15 viewport export; bilingual generateMetadata; iOS apple-touch-icon. E1 wastewater placeholder identity removed |
| s7.2 | Accessibility pass | **done** ✓ | WCAG 2.1 AA contrast audit + fixes; keyboard nav across all panels; axe-core scan (0 violations) |
| s7.3 | English translation pass | **done** ✓ | 172/172 EN keys reviewed; identical-value leak later caught and guarded in s7.1 |
| s7.4 | End-to-end demo flow validation | **done** ✓ | Full 10-step demo path in one run, 1.41s against the 600s NFR-01 budget. Repeatability asserted (BUG-05), CSV boundary asserted (BUG-06), LLM success path and degradation path both covered. Test proven able to fail via two deliberate breakages. **M4 harness written but SKIPPED — no PostgreSQL on this host** |

## Open blockers

- ✅ **RESOLVED — `npm run build`.** Was failing on 10 ESLint errors (8 from s6.2 `a717c42`,
  2 from s7.2 `1ff30fe` — the "8 + 3 = 11" recorded here was off by one). Fixed by BUG-01 with
  zero suppressions; `npm run build` is now a CI gate. The epic has a working production build
  for the first time since 2026-08-07.
- ⛔ **Real-Postgres E2E (E6 M4) — STILL OPEN, now the only blocker.** No PostgreSQL and no
  Docker on this WSL host; port 5432 refused throughout 2026-08-20 and `apt install postgresql`
  needs a password only Rodrigo can supply. **What changed:** the harness now exists
  (`backend/tests/test_e2e_demo_flow.py` + the `postgres_client` fixture) and runs on one
  command. Every test run prints that M4 is unverified, names the five stories that deferred
  it, and states that a skip is an open gate rather than a pass. It also now covers migration
  `0004`, added by BUG-05 today, whose backfill has never executed against any database.

## Defects found and fixed on the demo path (2026-08-20)

Five bugfix pipelines ran before s7.4 could be written, all on the demo path:

| Bug | Severity | Summary |
|---|---|---|
| BUG-01 | S1 | Production build red for 13 days; CI was red and normalized |
| BUG-02 | S2 | `/prioritized?category=` matched nothing in any casing, hidden by a vacuous test |
| BUG-03 | S1 | CSV scenarios unscorable — `status="pending"` matched no consumer. **Partial**; BUG-06 escalated |
| BUG-04 | S2 | Pinned `reference_date` crashed persist, silently guaranteeing non-reproducibility |
| BUG-05 | S1 | **Scoring was non-deterministic under a fixed seed** — four epics of work affected. ADR-011 |

## Open, escalated, not fixed

- **BUG-06** — a CSV-uploaded scenario cannot be supervised-trained: `create_from_csv` assigns
  `PaymentPattern.ON_TIME` to every client, so the labeller draws a single class. Not fixable
  by varying the pattern (deriving it from ageing is the leakage ADR-006 forbids; randomising
  it trains a confident model on noise). Needs an ADR on scoring unlabelled uploads.
- **13 `format:check` failures** — pre-existing, and `format:check` is in the manifest but
  absent from CI. Same pathology as BUG-01 one layer down. Recorded in BUG-01's retro.
