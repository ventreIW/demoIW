# E4 Scope — Intelligence Engine

**Status:** Active — authorized 2026-07-21 (Gustavo)
**Stories:** s4.2–s4.10 (s4.1 delivered out-of-band by `b15-i18n-setup`; s4.9 score persistence,
s4.10 score-persistence wiring added during the run — s4.10 surfaced by the M4 checkpoint)

## Objective

Turn a generated scenario (E3) into actionable intelligence: a 0–100 collectability score per
client with a High/Medium/Low category and a plain-language explanation, plus a prioritization
engine that combines score and outstanding amount into a per-case priority value with a Pareto
filter over expected recoverable value.

## Foundational decision — what the model predicts

Taken 2026-07-21, before any code. To be recorded as **ADR-006**.

The model predicts a **forward-simulated collection outcome**: given a client's present
snapshot, will their outstanding balance be collected within a **90-day horizon**.

- **Features** are the observable snapshot only.
- **Label** is a simulated future event, generated using the client's `_PatternProfile` as
  hidden truth — the same causal machinery ADR-004 established.

### Leakage guard (non-negotiable)

`payment_history_pattern` is the **generative cause** of every invoice and payment in the
dataset, and it is stored on the client record. It must **never** enter the feature set. A model
trained with it reaches near-perfect accuracy by reading the answer key.

Any story touching feature construction must assert this exclusion in a test.

### Why not the alternatives

| Rejected | Reason |
|---|---|
| Label mapped directly from `payment_history_pattern` | The model would be inverting the generator. High accuracy, little meaning — it recovers a hidden variable the features were produced from |
| Label = share of past invoices settled on time | Computed from the same payment rows the features come from; correlates trivially with `days_overdue`. Partial leakage |

## In scope

| Item | Story |
|---|---|
| Feature extraction from `RawDataset` → client-level feature frame | s4.2 |
| Forward-outcome labeller (90-day horizon simulation) | s4.2 |
| Labelled training set builder + train/test split **by client** | s4.2 |
| Leakage test asserting `payment_history_pattern` is absent from features | s4.2 |
| ADR-006 (prediction target + leakage guard) | s4.2 |
| Supervised propensity model, 0–100 score output | s4.3 |
| High/Medium/Low categorization thresholds | s4.3 |
| `IScoreRepository` port + SQLAlchemy adapter (entity/ORM/mappers already exist from E2) | s4.9 |
| Model evaluation metrics + baseline comparison | s4.3 |
| Top-factor / feature-contribution explanation per score | s4.4 |
| Priority value formula `f(score, outstanding_amount)` | s4.5 |
| Pareto filter (~80% of expected recoverable value) | s4.5 |
| Prioritized list API — sortable/filterable by amount, days overdue, category | s4.5 |
| Rescore-on-contact endpoint (consumed by E5) | s4.6 |
| Locale switcher UI | s4.7 |
| `GenerateScenarioForm` i18n retrofit (27 hardcoded strings) | s4.7 |
| Real-model LLM enrichment verification + visible degradation | s4.8 |

## Explicitly out of scope

| Item | Reason |
|---|---|
| Operations panel UI consuming the prioritized list | E5 |
| Communications generation | E5 |
| KPI dashboard / NL query | E6 |
| Full English translation pass | E7 |
| Model retraining UI / online learning | Parking lot — not needed for demo conviction |
| Cost tracking for LLM calls | Parking lot |

## Story assignment

| Story | Title | Owner | Parallel with | Prerequisites |
|---|---|---|---|---|
| s4.2 | Feature engineering & training set | Rodrigo | s4.7 | None — start immediately |
| s4.3 | Collectability scoring model | Rodrigo | s4.7 | s4.2 merged |
| s4.4 | Score explanation | Rodrigo | s4.5 | s4.3 merged |
| s4.5 — formula | Priority value + Pareto threshold definition | Rodrigo | s4.4 | s4.3 merged |
| s4.5 — API | Sort/filter/prioritized-list endpoint | Nano | s4.4 | s4.5 formula agreed |
| s4.6 | Rescore-on-contact endpoint | Nano | s4.7 | s4.3 merged |
| s4.9 | Score persistence — `IScoreRepository` + adapter | Nano | s4.2 | None — start immediately |
| s4.7 | i18n completion — switcher + s3.4 retrofit | Renata | s4.2, s4.3 | None — start immediately |
| s4.8 | LLM enrichment verification + visible degradation | Rodrigo | any | ⛔ `OPENROUTER_API_KEY` |

## Acceptance gate checklist

Every item must be verified against observable state at epic close, not assumed from story
completion. E3 closed with three of seven gate items unverified because that distinction was
not made.

- [~] Every client in an active scenario has a persisted `Score` with value, category and explanation
  — **mechanism delivered** (s4.9 repo + s4.10 `POST /{id}/score`, idempotent; unit/api tested).
  Full real-Postgres E2E confirmation is the outstanding M4 item (needs a running DB).
- [x] `payment_history_pattern` provably absent from the feature set — test in `test_feature_extractor.py` (s4.2)
- [x] Model beats a documented naive baseline on held-out clients — ROC-AUC 0.732–0.739 vs majority-class, ADR-007 (s4.3)
- [x] Train/test split **by client** — `test_build_training_set.py` (s4.2)
- [x] Score reproducible for a fixed scenario seed — seed-pinned pipeline (s4.2/s4.3)
- [x] Prioritized list returns Pareto subset, sortable/filterable — `test_prioritized_endpoint.py` + E2E (s4.5-API)
- [x] Rescore endpoint changes a score given a contact result — `test_rescore_endpoint.py` + E2E (s4.6)
- [x] Locale switcher changes language; `GenerateScenarioForm` no hardcoded strings — s4.7
- [x] `es.json` and `en.json` key sets identical — verified 56/56 at close
- [x] ADR-006 (prediction target + leakage guard) written — `dev/decisions/adr-006-*`
- [x] All tests pass (pytest 345 + vitest 49); `mypy app/` + `npm run typecheck` clean — verified at M4/close
- [x] All story retrospectives written — s4.2–s4.10 (10 retrospectives present)
- [x] **s4.8 fulfilled** (2026-07-27, Rodrigo) — verified against the real free Nemotron model; enriched flag + honest source + loud startup warning delivered

## Risks

| Risk | Mitigation |
|---|---|
| Model inverts the generator, producing meaningless accuracy | Forward-outcome label + leakage guard + naive-baseline comparison |
| `OPENROUTER_API_KEY` never arrives | s4.8 blocked; E5 s5.4 and E6 s6.3 also blocked. Escalate now, not at E5 planning — 3 of 6 modules ride on it against a 2026-08-14 demo |
| Score thresholds chosen arbitrarily | High/Med/Low cutoffs must be justified in s4.3, not hard-coded by feel |
| Pull board goes stale | E3's board misrepresented delivery for two weeks. Update on every story transition |

---

# Implementation Plan

Sequencing strategy: **risk-first**, with a dependency-driven critical path. The riskiest
element is the model itself (s4.3) — whether a logistic regression on snapshot features can
beat a naive baseline at all. Everything upstream of it exists to answer that question as
early as possible.

## Story sequence

| # | Story | Owner | Size | Depends on | Rationale | Unblocks |
|---|---|---|---|---|---|---|
| 1 | s4.2 Feature engineering & training set | Rodrigo | S | — | Nothing exists downstream without a labelled training set. Carries ADR-006 into code | s4.3 |
| 1 | s4.9 Score persistence port + adapter | Nano | XS | — | Independent of the model: entity, ORM and mappers already exist. Removes Nano's idle stretch | s4.3 |
| 1 | s4.7 i18n completion | Renata | S | — | Fully independent; repairs a live regression on `main` | — |
| 2 | s4.3 Collectability scoring model | Rodrigo | M | s4.2, s4.9 | **Highest-risk story.** Proves or disproves ADR-007 | s4.4, s4.5, s4.6 |
| 3 | s4.4 Score explanation | Rodrigo | S | s4.3 | Coefficient attribution; RF-02.3 | E5 case detail |
| 3 | s4.5-formula Priority value + Pareto | Rodrigo | S | s4.3 | Statistical decision, parallel with s4.4 | s4.5-API |
| 4 | s4.5-API Prioritized-list endpoint | Nano | S | s4.5-formula | Mechanical once the formula is fixed | E5 s5.1 |
| 4 | s4.6 Rescore-on-contact endpoint | Nano | S | s4.3 | Consumed by E5 s5.3 | E5 s5.3 |
| — | s4.8 LLM enrichment verification | Rodrigo | S | ⛔ API key | External blocker; not on the critical path | E5 s5.4, E6 s6.3 |

**Critical path:** s4.2 → s4.3 → s4.4 / s4.5-formula → s4.5-API. Everything else hangs off it
or runs beside it.

## Parallel work streams

```
Rodrigo   s4.2 ──────────→ s4.3 ──┬→ s4.4
                                  └→ s4.5-formula ──→ (hands to Nano)
Nano      s4.9 ───────────────────────────────────→ s4.5-API
                                   └→ s4.6
Renata    s4.7 ─────────────────────── (independent throughout)
```

All three developers have work from day one. Nano's s4.9 is deliberately placed to remove a
multi-day idle stretch that the original sequencing would have created.

## Milestones

### M1 — Walking skeleton: a scenario can be scored
**Stories:** s4.2, s4.9, s4.3

**Success criteria**
- [ ] A labelled training set is built from a generated scenario, reproducible for a fixed seed
- [ ] Test proves `payment_history_pattern` is absent from the feature frame
- [ ] Model trains and produces a 0–100 score per client
- [ ] **Model beats the documented naive baseline on held-out clients**
- [x] Scores persist and read back via `IScoreRepository` (port+adapter+tests, s4.9; pipeline wiring verified at M4)
- [ ] `days_overdue_max` carries a negative coefficient (sanity check on the whole pipeline)

**Demo:** generate a scenario, score it, show scores in the database.

**This milestone is the go/no-go for ADR-007.** If the model cannot beat the baseline, stop and
revise the ADR rather than proceeding to build explanation and prioritization on top of a model
that does not work.

### M2 — Core MVP: prioritized and explained
**Stories:** + s4.4, s4.5-formula, s4.5-API

**Success criteria**
- [ ] Each score carries a ranked top-3 factor explanation in plain language
- [ ] Priority value computed per case; Pareto subset returned
- [ ] Prioritized list API sortable/filterable by amount, days overdue, category
- [ ] Category thresholds justified against the score distribution, not chosen by feel

**Demo:** the full E4 thesis — "these 20 accounts hold 80% of your recoverable value, and here
is why each one scored as it did."

### M3 — Feature complete
**Stories:** + s4.6, s4.7

**Success criteria**
- [ ] Rescore endpoint changes a score given a contact result
- [ ] Locale switcher works; `GenerateScenarioForm` has no hardcoded strings
- [ ] `es.json` and `en.json` key sets identical

### M4 — E2E integration checkpoint + epic close
**Stories:** none new — verification only

Runs against a **real PostgreSQL instance**, not SQLite in-memory, across the full path:
generate scenario → score → prioritized list → record contact → rescore.

**Success criteria**
- [~] Full path works end-to-end — **in-process E2E passes** (`test_e2e_intelligence_path.py`: generate → score+persist → prioritized → rescore through the real app + repos over SQLite). **Real-Postgres run deferred** (no DB in the close environment) — see retrospective for the exact steps.
- [→] Frontend consumes the prioritized-list API — **deferred to E5** (the operations panel that consumes `/prioritized` is explicitly out of E4 scope per this doc's Out-of-scope table). API contract seam verified server-side by the E2E.
- [x] Every acceptance-gate item verified against observable state — done item-by-item at close (see retrospective)
- [x] s4.8 fulfilled (2026-07-27, Rodrigo) — real-model enrichment verified + degradation made visible
- [x] ADR-006 and ADR-007 still reflect what was built — unchanged by s4.8–s4.10 (enrichment + persistence, not the model); still accurate

This checkpoint exists because E3 closed with three of seven gate items unverified. Unit tests
with mocks cannot catch contract mismatches between stories; only real E2E does.

## Progress tracking

| Story | Owner | Status | Started | Merged | Notes |
|---|---|---|---|---|---|
| s4.2 | Rodrigo | ✅ **done** | 2026-07-21 | 2026-07-21 (#7) | ADR-006 validated: rates within 0.002 of prediction. 58 tests |
| s4.9 | Rodrigo (covering) | ✅ **done** | 2026-07-27 | 2026-07-27 | Port + adapter + provider over existing ScoreORM/mappers. 6 tests. Pipeline wiring deferred to M4 |
| s4.10 | Rodrigo | ✅ **done** | 2026-07-27 | 2026-07-27 | Score-persistence wiring (M4 finding). `POST /{id}/score` persists Scores, idempotent. 7 tests. Gate #1 mechanism delivered |
| s4.7 | Renata | ready | — | — | Can start immediately |
| s4.3 | Rodrigo | ✅ **done** | 2026-07-21 | 2026-07-21 (#8) | **M1 GO.** ROC-AUC mean 0.732–0.739; ADR-007 amended (C=0.01). Built without persistence — s4.9 still owns it |
| s4.4 | Rodrigo | ✅ **done** | 2026-07-21 | 2026-07-21 (#10) | RF-02.3 delivered. Direction-aware phrasing after a contradiction found by reading real output |
| s4.5-formula | Rodrigo | ready | — | — | s4.3 merged |
|| s4.5-API | Nano | ✅ **done** | 2026-07-22 | 2026-07-22 | 12 tests, contract verified, 422 validation |
| s4.6 | Nano | ✅ **done** | 2026-07-22 | 2026-07-22 | 6 tests, score heuristics, Pareto recomputed |
| s4.8 | Rodrigo | ✅ **done** | 2026-07-27 | 2026-07-27 | Verified vs free Nemotron; `enriched` flag + honest `source` + startup warning. Backend 331 tests |

## Sequencing risks

| Risk | Mitigation |
|---|---|
| **s4.3 fails the baseline check.** If logistic regression on snapshot features cannot beat majority-class, s4.4/s4.5/s4.6 are all built on sand | M1 is an explicit go/no-go. Fail fast there, revise ADR-007, do not proceed on hope |
| **s4.3 gates four downstream stories.** A delay there stalls both Rodrigo and Nano | s4.9 and s4.7 keep the other two moving; s4.4 and s4.5-formula are parallel once s4.3 lands |
| **The API key never arrives.** s4.8 stays blocked and takes E5 s5.4 and E6 s6.3 with it | Escalate now, not at E5 planning. 3 of 6 modules against a 2026-08-14 demo |
| **Plans are hypotheses.** This sequence assumes s4.2's labeller is ~1 day | Re-sequence at M1 if it is not. Do not defend the plan against evidence |
