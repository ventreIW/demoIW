# E4 Design — Intelligence Engine

**Status:** Active — authorized 2026-07-21
**Companion:** `scope.md` (WHAT + WHY). This document is HOW.

## Gemba findings

Read before designing. What already exists in `backend/`:

| Finding | Consequence for E4 |
|---|---|
| `Score` entity (`app/domain/entities/score.py`) exists — `score_value`, `category`, `explanation`, `scored_at` | **Reuse. Do not re-model.** The shape already fits RF-02.1–02.3 |
| `ScoreORM` table and both mappers (`score_orm_to_domain`, `score_domain_to_orm`) exist | Persistence layer is half-built already |
| **No `IScoreRepository`** — ports cover Scenario, Client, Invoice, Payment only | **New work, unaccounted for in the original story list.** Added to s4.3 |
| No scoring, ML or prediction code anywhere | Greenfield — no duplication risk, no legacy to work around |
| **No ML library** — `numpy==2.2.1`, `pandas==2.2.3` only | s4.3 introduces `scikit-learn`. Architectural decision → ADR-007 |
| `ProceduralGenerator._PATTERN_PROFILES` holds the causal behaviour model (ADR-004) | The labeller reuses these profiles as hidden truth. Do not duplicate the constants — import them |
| Hexagonal structure holds throughout (ports/adapters/use-cases/container) | Follow it. Scoring is an adapter behind a port, wired in `container.py` |
| `RawDataset` is the DataFrame carrier (clients/invoices/payments) | Feature extraction consumes it directly — no new transport type |
| No `governance/drift-hotspots.json` | Module health check skipped |

## Key decisions

Both recorded as ADRs before implementation.

### ADR-006 — Prediction target and leakage guard

The model predicts a **forward-simulated collection outcome**: given a client's present
snapshot, will their outstanding balance be collected within **90 days**.

`payment_history_pattern` is the generative cause of every invoice and payment and is stored on
the client record. **It must never enter the feature set.** Enforced by test.

### ADR-007 — scikit-learn with logistic regression

`LogisticRegression`, trained **on demand per scenario**. Chosen because s4.4 requires a
per-score explanation: coefficient × centred feature value yields a ranked top-factor list with
no additional dependency. Gradient boosting would score better but needs SHAP for per-prediction
attribution — a second dependency and a harder story to tell a non-technical audience.

Scenarios are 10–500 clients, so training is sub-second. No model artifact is persisted: no
versioning, no staleness, no "which scenario was this trained on" ambiguity.

## Target components

```
app/
  domain/
    entities/score.py                  EXISTS — reuse unchanged
    value_objects/
      client_features.py               NEW  s4.2  feature row schema
      training_set.py                  NEW  s4.2  X / y + split metadata
  ports/
    scoring_port.py                    NEW  s4.3  IScoringPort
    repositories.py                    EXTEND s4.3  + IScoreRepository
  application/
    services/
      feature_extractor.py             NEW  s4.2  RawDataset -> feature frame
      outcome_labeller.py              NEW  s4.2  90-day forward simulation
      score_explainer.py               NEW  s4.4  coef x value -> top factors
      prioritizer.py                   NEW  s4.5  priority value + Pareto
    use_cases/
      build_training_set.py            NEW  s4.2
      score_scenario.py                NEW  s4.3
      rescore_on_contact.py            NEW  s4.6
  adapters/
    scoring/
      sklearn_scorer.py                NEW  s4.3  IScoringPort impl
    persistence/
      sqlalchemy_score_repo.py         NEW  s4.3  IScoreRepository impl
  routers/
    scores.py                          NEW  s4.3/s4.5/s4.6 endpoints
```

Frontend (s4.7) touches `MainLayout` (switcher) and `GenerateScenarioForm` (retrofit) only.

## Key contracts

### Feature row — s4.2

One row per client, derived from the snapshot. **`payment_history_pattern` is excluded.**

| Feature | Type | Source |
|---|---|---|
| `days_overdue_max` | float | max over the client's open invoices |
| `days_overdue_mean` | float | mean over open invoices |
| `outstanding_amount` | float | sum of unsettled invoice amounts |
| `invoice_count` | int | total invoices |
| `avg_invoice_amount` | float | mean amount |
| `pct_invoices_settled` | float | settled / total |
| `avg_days_late_historical` | float | mean lateness of settled invoices |
| `has_partial_payments` | bool | any invoice with a partial payment |
| `sector` | categorical | one-hot |

### Label — s4.2

`collected_within_90d ∈ {0, 1}`, simulated per client from its `_PatternProfile`. Uses the
scenario's seeded RNG so the training set is reproducible for a fixed seed.

### `IScoringPort` — s4.3

```python
class IScoringPort(ABC):
    @abstractmethod
    def fit(self, training_set: TrainingSet) -> None: ...

    @abstractmethod
    def predict_scores(self, features: pd.DataFrame) -> pd.Series:
        """0-100 collectability score per client."""

    @abstractmethod
    def explain(self, features: pd.DataFrame) -> list[list[FactorContribution]]:
        """Ranked top factors per client, for s4.4."""
```

Keeps the epic model-agnostic in the same way `ILLMPort` keeps it provider-agnostic — a stated
project guardrail.

### Priority value — s4.5

`priority = f(score, outstanding_amount)`; exact form decided in s4.5 and justified there, not
hard-coded by feel. Pareto filter returns the subset holding ~80% of expected recoverable value,
where expected recoverable = `outstanding_amount × (score / 100)`.

## Train/test discipline

- Split **by client**, never by invoice — the same client must not appear in both sides
- Compare against a documented naive baseline (majority class) — a model that cannot beat it is
  not shipping intelligence
- Score reproducibility for a fixed scenario seed is an acceptance-gate item

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Model inverts the generator, giving meaningless high accuracy | Medium | High | ADR-006 forward-outcome label; leakage test; naive-baseline comparison |
| `OPENROUTER_API_KEY` never arrives | High | High | s4.8 blocked, and so are E5 s5.4 / E6 s6.3. Escalate now — 3 of 6 modules, demo 2026-08-14 |
| Category thresholds set arbitrarily | Medium | Medium | High/Med/Low cutoffs justified in s4.3 against score distribution, not chosen by feel |
| Simulated label is itself an artefact of `_PATTERN_PROFILES` | Medium | Medium | Acknowledged: the data is synthetic, so any label descends from the generator. The guard is that features are the *observable* projection, and the model never sees the cause |

## Waste check

Every story tests as essential:

- s4.2 → without it there is no training set; nothing downstream exists
- s4.3 → the epic objective is the score
- s4.4 → RF-02.3, and the demo needs explanations to be convincing
- s4.5 → RF-03, the Pareto filter is the product thesis
- s4.6 → E5 s5.3 consumes it; without it, recording a contact does nothing
- s4.7 → repairs a live regression on `main`
- s4.8 → E3's descoped gate item; the AI half is still unverified
