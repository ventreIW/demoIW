# Pull Board — e6: Executive Panel

Last updated: 2026-08-11 (s6.4 closed)

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|
| s6.0 | OpenRouter adapter hardening | — | **done** | Merged to `main` 2026-08-04. Adapter raises ExternalServiceError for missing choices and timeout. |
| s6.1 | KPI aggregation — backend | Rodrigo | **done** | Merged to `main` 2026-08-04. Retrospective written |
| s6.2 | Executive dashboard + segmentation — frontend | — | **done** | Merged to `main` 2026-08-07 (`13c2389`→`346e024`, fast-forward — no merge commit). Retrospective written 2026-08-11. **M2 complete.** Live E2E deferred: AC3 (NFR-02 at 500 clients) unverified, no Postgres |
| s6.3 | NL query — backend | Rodrigo | **done** | Merged to `main` 2026-08-11 (`--no-ff`). 545 tests, 9/9 live translation hit rate. ADR-008 amended. Retrospective written. **M3 backend complete** |
| s6.4 | NL query — frontend | — | **done** | Merged to `main` 2026-08-11 (`--no-ff`). `NlQueryPanel` POSTs to `/query`; renders answerable=true (chart+narrative+citation), answerable=false refusal with examples from API `supported` vocabulary (no hardcoded list), or error/retry. Null narrative renders chart w/o paragraph. 151/151 frontend tests, tsc/lint/format clean. Retrospective written. **M3 complete — full P-02 loop demoable (dashboard → ask → chart+narrative+citation).** Live E2E still open (no Postgres) — M4 |

**WIP limit:** 2 in-progress per epic (GR-PROC-003).
**Cut line — RESOLVED 2026-08-11: E6 continues, s6.3/s6.4 are NOT cut.**
Two reasons. M2 landed 2026-08-07, ahead of the 08-09 condition. And the 2026-08-14 demo date is
**not hard** — Rodrigo confirmed it can move — which removes the schedule pressure the cut line was
built on. Treat the date-driven urgency in `scope.md` §Sequencing risks as stale; the E7 squeeze it
describes is not the live constraint. Quality gates and the M4 E2E requirement still bind normally.
