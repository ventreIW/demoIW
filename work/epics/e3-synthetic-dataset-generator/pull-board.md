# Pull Board — E3: Synthetic Dataset Generator

Last updated: 2026-07-20  
Epic: logical container (no branch)  
Status: **CLOSED** — 2026-07-20, tag `epic/e3-complete`. See `retrospective.md`.

---

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|
| s3.1 | Procedural data generation layer | Rodrigo | done | Merged; ADR-003 + ADR-004 |
| s3.2 | OpenRouter adapter | Nano | done | Implemented and tested (mocked HTTP) |
| s3.3 | LLM enrichment layer | — | done | Batched 20/client per ADR-005 |
| s3.4 | Generate scenario endpoint & UI | — | done | Endpoint, repos, generation form |

> **Board was stale from 2026-07-07 to 2026-07-20**, showing s3.1 *in progress* and
> s3.3/s3.4 *backlog* while all four had in fact merged. Corrected at epic close.
> Keeping the board current is a stated project rule; it did not happen here, and the
> board actively misrepresented delivery for two weeks.

**Closed with one acceptance-gate item descoped:** LLM enrichment has never run against a
real model (no `OPENROUTER_API_KEY`). Owned by s4.8. See `scope.md`.

---

## Execution order

```
s3.1 ─┐
       ├─► s3.3 ─► s3.4
s3.2 ─┘
```

s3.1 and s3.2 can be developed in parallel.
