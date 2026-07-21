# Scoring & Prioritization Decisions

> How demoIW turns a generated portfolio into a **ranked collections queue** — the model, what it
> predicts, why the number means what it says, and where the honest limits are. Written so a
> non-statistician can follow it and a statistician can audit it.
>
> Companion to [02 — Probability & Statistics Decisions](02-probability-and-statistics-decisions.md),
> which covers how the data is *made*. This doc covers how it is *modelled*.
>
> Canonical decisions live in [ADR-006](../dev/decisions/adr-006-prediction-target-and-leakage-guard.md)
> and [ADR-007](../dev/decisions/adr-007-sklearn-logistic-regression.md). This explains the *why*
> in one place.

---

## 1. The hardest problem: what should the model predict?

The generator produces a **snapshot**, not a resolved history. There is no "did this client
eventually pay" column to learn from. So the target had to be constructed — and the obvious
construction is a trap.

Every client carries a `payment_history_pattern` (on-time, delayed-30, …, default) which, per
[ADR-004](../dev/decisions/adr-004-pattern-driven-behavioral-model.md), **generates every invoice
and payment that client has**. It is also stored on the client record.

**The trap.** Map that pattern to a collectability class and train on it. The model scores near
100% — because it is reading the variable that produced its own answers. Impressive number, zero
meaning: the model would have learned to invert the generator, not to predict payment.

**The decision (ADR-006).** The model predicts a **forward-simulated collection outcome**: given a
client's present snapshot, will their outstanding balance be collected within **90 days**?

| | |
|---|---|
| **Features** | The observable snapshot only — invoice ageing, balances, settlement history, sector |
| **Label** | A *future* event, simulated per client from that client's own behaviour profile |

Features and label are separated by a **time boundary**. That is what makes the score a prediction
rather than a lookup.

### The leakage guard is enforced, not remembered

`payment_history_pattern` may **never** enter the feature set. This is guarded three ways: the
column is never selected, a `FORBIDDEN_COLUMNS` assertion runs inside feature extraction, and a
test fails loudly if it is ever reintroduced.

> **Deliberate asymmetry:** the *labeller* does read the pattern, because it is the hidden truth
> being simulated from. Only the *features* must never see it.

### Honest caveat

On synthetic data every label ultimately descends from the generator. The guard is that the model
sees only the **observable projection** of the cause, never the cause itself — which is precisely
the position a real collections model is in.

---

## 2. What the label looks like in practice

For each client with an outstanding balance, time-to-collection is drawn as
**Exponential(mean = `late_days_mean`)** from that client's profile. The label is `1` when it
lands inside the 90-day horizon.

The ADR predicted these rates; the implementation reproduced them **within 0.002** (n = 3000 per
cohort):

| Payment pattern | Predicted P(collect ≤ 90d) | Measured |
|-----------------|:--------------------------:|:--------:|
| ON_TIME | ~1.00 | **1.000** |
| DELAYED_30 | ~0.95 | **0.944** |
| DELAYED_60 | ~0.78 | **0.777** |
| DELAYED_90_PLUS | ~0.59 | **0.588** |
| PARTIAL | ~0.83 | **0.836** |
| DEFAULT | ~0.43 | **0.428** |

Separation between best and worst cohort is ~0.57 — comfortably learnable.

**Clients with nothing outstanding are excluded, not labelled.** "Will it be collected" is
undefined when there is nothing to collect. They are counted and reported rather than silently
dropped or defaulted to a value.

---

## 3. Why accuracy is the wrong metric here

The label design forces a consequence that must not be discovered later: roughly **80% of
labellable clients collect within 90 days**. Measured positive-class rate by sector:

| Sector | Positive rate | Majority-class accuracy |
|--------|:-------------:|:-----------------------:|
| Manufacturing | 0.823 | 0.823 |
| Retail | 0.753 | 0.753 |
| Professional services | 0.856 | 0.856 |

A model that predicts "everyone pays" therefore scores **75–86% accuracy while being useless**.

**So the quality gate is ROC-AUC**, which is threshold-free and measures *ranking* — exactly what
prioritization consumes. Balanced accuracy is reported at the chosen category cutoff, never at a
naive 0.5 probability cutoff, and the majority-class baseline is always shown alongside so no
figure can be read without its context.

---

## 4. The model, and why it is a *linear* one

**Logistic regression over standardised features, trained on demand per scenario, no persisted
artifact** (ADR-007).

The binding constraint was **not** accuracy. It was RF-02.3: every score must carry a
plain-language explanation of the factors behind it — *per client*, not on average. A linear model
decomposes exactly: `contribution = coefficient × standardised value`. Gradient boosting would
score better and require a second library (SHAP) to attribute a single prediction, producing
explanations that are harder to defend to a collections officer.

### Feature scaling is mandatory, not stylistic

Unscaled, the optimiser failed to converge **and produced inverted coefficient signs** —
`pct_invoices_settled` came out negative, i.e. a model asserting that clients who settle their
invoices are *less* collectable. `outstanding_amount` is on the order of 10⁴ while
`pct_invoices_settled` is on the order of 10⁰; without standardisation the fit is meaningless.

### Strong regularization, for a reason that is not overfitting

`C = 0.01` — one hundred times stronger than the library default.

The features are collinear by construction:

| Feature pair | Correlation |
|---|---:|
| `days_overdue_max` ↔ `days_overdue_mean` | **0.872** |
| `days_overdue_max` ↔ `pct_invoices_settled` | −0.413 |

With collinear predictors the fit splits their weight arbitrarily, and the split **moves with the
random seed**. At the default `C = 1.0`, **19 of 27** configurations produced a positive
coefficient on `days_overdue_max` — a model stating that being further overdue makes a client more
collectable. Ranking was fine throughout; only the explanations would have been wrong.

Stronger ridge shrinks correlated coefficients toward each other instead of letting them fight:

| Setting | Wrong-signed coefficients | Mean ROC-AUC |
|---|---:|---:|
| `C = 1.0` (default) | 19/27 | 0.716 |
| `C = 0.1` | 4/27 | 0.725 |
| **`C = 0.01`** | **0/45** | **~0.735** |

Regularization bought stability **and** improved mean AUC.

> **The general lesson:** ranking quality and explanation quality are independent properties, and
> only one of them appears in the headline metric.

---

## 5. Measured model quality

Across 45 configurations — 3 sectors × 3 scenario sizes × 5 seeds:

| Scenario size | ROC-AUC min | ROC-AUC mean | Wrong-signed coefficients |
|---|---:|---:|---:|
| 200 clients | 0.622 | 0.739 | 0/15 |
| 400 clients | 0.577 | 0.734 | 0/15 |
| 1000 clients | 0.666 | 0.732 | 0/15 |

**Retail is consistently the weakest sector** (AUC 0.605–0.710 vs manufacturing 0.681–0.819). Its
mix carries the highest share of partial payers, who sit mid-gradient, so the classes overlap
more. Worth knowing when choosing which sector to demo.

### The gate is two-part, because a single run is noisy

- **Per-run floor: 0.55** — catches a genuinely broken model
- **Mean across seeds: ≥ 0.65** — the actual quality signal (measured 0.732–0.739)

A strict single-run threshold on a noisy metric produces flaky builds and tempts people to lower
the gate.

### Small scenarios cannot be evaluated at all

Below **30 held-out clients**, metrics are **withheld** and the status reports
`insufficient_data`. At 100 clients the measured AUC ranged from **0.286 to 1.000** across seeds —
worse than chance to perfect — because ~100 clients yields ~60 scoreable and an ~18-row test set.
Publishing either figure as a quality signal would be worse than publishing none.

**Consequence for users:** scenarios below ~200 clients should not be trusted, and the generation
form enforces a 200-client minimum.

---

## 6. From probability to a score anyone can read

The score is **`P(collected within 90 days) × 100`**, and it is a *genuine* probability.

That required refusing a tempting option. `class_weight="balanced"` improves balanced accuracy on
an 80/20 problem — but it destroys calibration, and `predict_proba` stops estimating anything
real. A score of 34 would no longer mean "roughly 34% likely to pay"; it would be an index.

We kept calibration. **A director reading 34 is reading a probability.** The cost is that balanced
accuracy at a naive 0.5 cutoff looks weak — a property of the threshold, not the model, and stated
explicitly wherever it could mislead.

### Category bands

| Category | Score | Observed share |
|---|---|---:|
| Low | < 40 | ~25% |
| Medium | 40 – 70 | ~50% |
| High | > 70 | ~25% |

Chosen against the measured distribution (p25 = 40.3, p50 = 53.4, p75 = 67.5), not by feel. They
are **fixed absolutes rather than per-scenario terciles**, so the same client lands in the same
band regardless of which portfolio it sits in, and re-scoring after contact moves a band only when
that client actually changes.

---

## 7. Explaining a score without saying "coefficient"

Every score carries one Spanish sentence naming what drove it.

**Correlated features are grouped before ranking.** `days_overdue_max` and `days_overdue_mean`
measure the same thing; their contributions correlate at 0.885, and **26.2% of clients have both
in their top tier**. Without grouping, more than a quarter of explanations would state overdue
ageing twice. Grouping happens *before* ranking, so the combined signal competes fairly rather
than splitting its own weight.

**Only material factors are named.** A factor must reach **30% of that client's largest
contribution**, capped at three. Measured decay by rank is 1.00 / 0.72 / 0.48 / 0.36, so this
yields two or three factors typically — and exactly one when a single driver dominates.

**Framing follows the sign, not the value.** A *positive* ageing contribution means the client is
less overdue than the portfolio average. An early version rendered the bare fact and produced:

```
Buen perfil de pago: facturas con hasta 40 días de atraso
```

"Good payment profile: invoices up to 40 days overdue." Every rule was individually correct and
the sentence contradicted itself. The same fact is now framed by the sign that selected it:

| Factor | Favourable | Unfavourable |
|---|---|---|
| Ageing | `atraso contenido, de hasta 40 días` | `facturas con hasta 480 días de atraso` |
| Partial payments | `pagos parciales recibidos` | `pagos parciales pendientes` |
| Settlement | `5 de 7 facturas liquidadas` | `sólo 2 de 7 facturas liquidadas` |

No LLM is involved. Template text over exact numeric contributions is **deterministic** — the same
seeded scenario always yields the same explanation — and works without an API key.

---

## 8. Prioritization: ranking by money, not by score

**Priority = `outstanding_amount × score / 100`** — the **expected recoverable value, in pesos**.

The units are real *only because* §6 kept the probability calibrated. Had the model been optimised
for balanced accuracy, this product would be an index and every claim built on it would be
arithmetic without meaning.

Why the product and not either input alone:

| Ranking by | Failure mode |
|---|---|
| Score alone | Collectors chase cheap certainties — a 95-score client owing $200 leads the queue |
| Amount alone | Collectors chase large uncollectables — the exact behaviour the scoring engine exists to correct |
| **Expected value** | A 30-score client owing $100,000 ($30,000 expected) correctly outranks a 90-score client owing $30,000 ($27,000) |

The **Pareto subset** is the *smallest* prefix of that ranking whose cumulative expected value
reaches 80%. Minimality is the requirement — the whole portfolio also holds 100% of its own value,
so a filter returning everything would be technically correct and operationally useless.

### ⚠️ This portfolio is **not** Pareto-distributed

The name invites "20% of accounts hold 80% of the value". Measured, it does not:

| Top X% of clients | Share of expected recoverable value |
|---:|---:|
| 5% | 13.2% |
| **20%** | **40.1%** |
| 30% | 53.5% |
| 50% | 73.4% |
| **58%** | **80%** |

Consistent across all three sectors (39.9 / 40.1 / 40.5).

**The cause is upstream, in the generator, not in the formula.** Invoice amounts are drawn from
**Normal**(10,000, 3,000) — a tight distribution where every client holds a similar balance, so
concentration can only come from score variation. Real receivables books are **heavy-tailed**: a
handful of large clients dominate, which is exactly what makes Pareto filtering valuable.

The system therefore reports the **measured** figure — *"159 de 271 cuentas concentran 80.0% del
valor recuperable esperado"* — and never an inherited 20/80 claim. A test exists specifically to
fail if anyone reintroduces it.

**To get a real Pareto story**, the generator needs a log-normal amount distribution. That is a
small change with a large blast radius (it invalidates the seed-42 fixtures several test suites
pin), so it is parked as its own story rather than applied quietly.

---

## 9. Assumptions & limitations (read before quoting numbers to a client)

Beyond the generation limits in [doc 02 §8](02-probability-and-statistics-decisions.md):

- **The model is trained on synthetic data whose labels descend from the generator.** AUC ~0.73
  measures how well observable features recover a simulated outcome — not real-world collections
  performance.
- **Trained per scenario, on demand.** No model is persisted, so there is no cross-scenario
  learning and `sector` carries no signal (it is constant within a scenario, so it was dropped
  from the feature set entirely).
- **The 90-day horizon is a modelling choice**, aligned with the `delayed_90_plus` boundary. A
  different horizon changes the class balance and therefore every downstream figure.
- **Expected-value ranking chases collectable money, not the riskiest accounts.** A 30-score
  client needs a very large balance to outrank a 70-score one. This is the difference between
  *maximising recovery* and *preventing write-offs* — a policy choice, deliberately not encoded
  as a fudge factor.
- **Small accounts are permanently deprioritised.** An 83.6-score client owing $1,108 ranks last
  in a 271-account portfolio despite being cheap to collect. Workload policy, not a formula fix.
- **Retail — the likeliest demo sector — is the weakest performer.** Choose deliberately.

---

## 10. How we verify all of this

| What's checked | Where |
|---|---|
| `payment_history_pattern` never reaches the model | `test_feature_extractor.py::test_leakage_guard_pattern_absent_from_features` |
| Label carries real signal (on-time vs default separation) | `test_outcome_labeller.py::test_on_time_cohort_collects_more_than_default` |
| Same seed → identical features, labels, scores, explanations, ranks | determinism tests in every suite |
| Train/test split never shares a client | `test_build_training_set.py::test_split_is_disjoint_by_client` |
| **Coefficient signs are correct and stable across seeds** | `test_sklearn_scorer.py::test_coefficient_directions`, `test_score_scenario_integration.py::test_coefficient_signs_stable_across_seeds` |
| Feature scaling is present | `test_sklearn_scorer.py::test_pipeline_includes_a_scaler` |
| Score stays a calibrated probability (no `class_weight`) | `test_sklearn_scorer.py::test_no_class_weight_is_applied` |
| **Model beats the AUC gate on real scenarios, all sectors** | `test_score_scenario_integration.py::test_auc_above_gate_on_real_scenarios` |
| Small test sets report `insufficient_data`, never a number | `test_evaluation_metrics.py::test_small_test_set_reports_insufficient_data` |
| Ageing is never stated twice in one explanation | `test_score_explanation_integration.py::test_no_client_gets_ageing_twice` |
| Pareto subset is the **smallest** qualifying prefix | `test_prioritizer.py::test_pareto_returns_smallest_qualifying_prefix` |
| The 20/80 claim cannot be reintroduced | `test_prioritize_scenario_integration.py::test_top_twenty_percent_holds_far_less_than_eighty_percent` |
| `sklearn` never leaks outside its adapter | `test_score_explanation_integration.py::test_sklearn_not_imported_in_application_or_domain_layers` |

If any assumption drifts, a test fails — so this document and the code stay in sync.
