# E4 Scope — Intelligence Engine

**Status:** Active — authorized 2026-07-21 (Gustavo)
**Stories:** s4.2–s4.8 (s4.1 delivered out-of-band by `b15-i18n-setup`)

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
| `Score` entity persistence (reuse E2 entity — do not re-model) | s4.3 |
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
| s4.7 | i18n completion — switcher + s3.4 retrofit | Renata | s4.2, s4.3 | None — start immediately |
| s4.8 | LLM enrichment verification + visible degradation | Rodrigo | any | ⛔ `OPENROUTER_API_KEY` |

## Acceptance gate checklist

Every item must be verified against observable state at epic close, not assumed from story
completion. E3 closed with three of seven gate items unverified because that distinction was
not made.

- [ ] Every client in an active scenario has a persisted `Score` with value, category and explanation
- [ ] `payment_history_pattern` is provably absent from the feature set (test asserts it)
- [ ] Model beats a documented naive baseline (e.g. "predict majority class") on held-out clients
- [ ] Train/test split is **by client** — no client appears in both
- [ ] Score is reproducible for a fixed scenario seed
- [ ] Prioritized list returns the Pareto subset and is sortable/filterable by amount, days overdue, category
- [ ] Rescore endpoint changes a score given a contact result
- [ ] Locale switcher changes language from within the app; `GenerateScenarioForm` has no hardcoded strings
- [ ] `es.json` and `en.json` key sets are identical
- [ ] ADR-006 (prediction target + leakage guard) written
- [ ] All tests pass (pytest + vitest); `mypy app/` and `npm run typecheck` clean
- [ ] All story retrospectives written
- [ ] **s4.8 either fulfilled or explicitly descoped again with a named owner** — do not let it lapse silently a second time

## Risks

| Risk | Mitigation |
|---|---|
| Model inverts the generator, producing meaningless accuracy | Forward-outcome label + leakage guard + naive-baseline comparison |
| `OPENROUTER_API_KEY` never arrives | s4.8 blocked; E5 s5.4 and E6 s6.3 also blocked. Escalate now, not at E5 planning — 3 of 6 modules ride on it against a 2026-08-14 demo |
| Score thresholds chosen arbitrarily | High/Med/Low cutoffs must be justified in s4.3, not hard-coded by feel |
| Pull board goes stale | E3's board misrepresented delivery for two weeks. Update on every story transition |
