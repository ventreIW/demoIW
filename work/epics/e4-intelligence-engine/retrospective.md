# E4: Intelligence Engine — Retrospective

**Closed:** 2026-07-27 · **Status:** Closed (one item explicitly deferred — see below)
**Stories:** s4.1–s4.10 (s4.1 out-of-band via `b15`) · **Backend:** 345 tests · **Frontend:** 49 tests

## Objective (met)
Turn a generated scenario into actionable intelligence: a 0–100 collectability score per client
with High/Med/Low + plain-language explanation, plus a prioritization engine (value × probability,
Pareto filter). Delivered end to end and verified by an in-process full-path E2E.

## Stories delivered
| Story | What | Status |
|---|---|---|
| s4.2 | Feature engineering + training set (ADR-006) | ✅ |
| s4.3 | Collectability scoring model (M1 GO, ADR-007 C=0.01) | ✅ |
| s4.4 | Score explanation (direction-aware) | ✅ |
| s4.5 | Priority value + Pareto + prioritized API | ✅ |
| s4.6 | Rescore-on-contact endpoint | ✅ |
| s4.7 | i18n completion (switcher + retrofit) | ✅ |
| s4.8 | LLM enrichment verification + visible degradation | ✅ (this session) |
| s4.9 | Score persistence — IScoreRepository + adapter | ✅ (this session) |
| s4.10 | Score-persistence wiring (`POST /{id}/score`) | ✅ (this session, M4-surfaced) |

## Acceptance-gate verification (item-by-item against observable state)
All gates met except one deferred:
- Leakage guard, split-by-client, reproducible seed, beats-baseline (ROC-AUC 0.732–0.739),
  prioritized Pareto+sort/filter, rescore-changes-score, locale switcher + no hardcoded strings,
  **es/en parity 56/56**, ADR-006 written, all tests green, mypy+typecheck clean, 10 retrospectives — **all ✅**.
- **Gate #1 (persisted Score per client):** mechanism delivered (s4.9 repo + s4.10 endpoint, idempotent)
  and exercised by the E2E (scores persist and read back). Literal **real-Postgres** confirmation deferred.
- **Full-path E2E:** in-process pass (`test_e2e_intelligence_path.py`) over the real app + repos (SQLite).
- **Frontend consumes prioritized API:** deferred to **E5** — the operations panel is explicitly out of E4 scope.
- **ADR-006/007:** unchanged by s4.8–s4.10 (enrichment + persistence, not the model) — still accurate.

## Elimination / commitment sweep
No elimination commitments in E4 (net-new epic). Every "In scope" item maps to a merged story; the
one gap the sweep found (scores computed but never persisted) was fixed mid-close by s4.10.

## What went well
- **M4 earned its cost twice.** It caught (a) score-persistence was never wired — three stories of
  green mocked tests had hidden it — spawning s4.10; and (b) a latent generation bug (pinning
  `reference_date` crashes persistence: date not JSON-serializable) on the E2E's first run.
- **Honest degradation as a design value** (s4.8): a ground-truth `EnrichmentOutcome` + `enriched`
  flag + honest `source` + startup warning, so a dead AI subsystem is never indistinguishable from a live one.
- **Greened a red main** that predated this session (s4.5 backend lint/format, b15/s4.7 prettier, and a
  b15 vitest next-intl resolution regression) — all four gate scripts pass.
- Free-tier procurement unblocked (OpenRouter + free Nemotron) with per-developer keys, ending the
  standing blocker on 3 of 6 modules.

## What to improve / carried forward (parking lot)
- **`reference_date` persistence bug** — pinning it (the reproducibility feature) crashes scenario
  persist. Own bugfix story. *(found by M4 E2E)*
- **Prioritized endpoint re-scores live** and ignores persisted scores — a follow-up should read them.
- **OpenRouterAdapter `KeyError`** on non-`choices` bodies (free-tier hiccup) — harden.
- **English enrichment output** for a Spanish UI — prompt-tuning.
- **Real-Postgres E2E** — run the full path against a live DB (below).

## Deferred item — real-Postgres E2E (the one open gate)
The scope requires the full path against real PostgreSQL (FK enforcement, type coercion). No DB was
available at close. To complete it:
```bash
# 1. start Postgres (example)
docker run -d --name demoiw-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=demoiw -p 5432:5432 postgres:16
# 2. point the app at it + migrate
cd backend && export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/demoiw
.venv/bin/alembic upgrade head
# 3. drive the full path (generate → score → prioritized → rescore) against it,
#    e.g. via the running app + the same calls as test_e2e_intelligence_path.py
```

## Process insight
Mock-based unit tests can stay green while an end-to-end contract is unmet; the observable-state
checkpoint (M4) is what converts "all stories merged" into "the epic actually works." E3 closed with
3/7 gates unverified — E4 did not repeat it.

## Learning chain
`.raise/rai/learnings/` absent project-wide (metrics N/A); graph PRIME returned 0 (wrong-root issue).
Both are standing framework parking-lot items, unchanged by this epic.
