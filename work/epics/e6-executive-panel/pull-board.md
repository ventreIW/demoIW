# Pull Board — e6: Executive Panel

Last updated: 2026-08-11

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|
| s6.0 | OpenRouter adapter hardening | — | **done** | Merged to `main` 2026-08-04. Adapter raises ExternalServiceError for missing choices and timeout. |
| s6.1 | KPI aggregation — backend | Rodrigo | **done** | Merged to `main` 2026-08-04. Retrospective written |
| s6.2 | Executive dashboard + segmentation — frontend | — | **done** | Merged to `main` 2026-08-07 (`13c2389`→`346e024`, fast-forward — no merge commit). Retrospective written 2026-08-11. **M2 complete.** Live E2E deferred: AC3 (NFR-02 at 500 clients) unverified, no Postgres |
| s6.3 | NL query — backend | — | **next** | **Unblocked** — s6.0 done, s6.1 aggregate on `main` |
| s6.4 | NL query — frontend | — | backlog | Blocked on s6.3 only — s6.2 has landed |

**WIP limit:** 2 in-progress per epic (GR-PROC-003).
**Cut line — RESOLVED 2026-08-11: E6 continues, s6.3/s6.4 are NOT cut.**
Two reasons. M2 landed 2026-08-07, ahead of the 08-09 condition. And the 2026-08-14 demo date is
**not hard** — Rodrigo confirmed it can move — which removes the schedule pressure the cut line was
built on. Treat the date-driven urgency in `scope.md` §Sequencing risks as stale; the E7 squeeze it
describes is not the live constraint. Quality gates and the M4 E2E requirement still bind normally.
