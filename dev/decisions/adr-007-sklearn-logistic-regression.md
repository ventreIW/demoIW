# ADR-007: scikit-learn with Logistic Regression, Trained On Demand

**Date:** 2026-07-21
**Status:** Accepted — **amended 2026-07-21** (see *Amendment 1: regularization strength*)
**Epic:** e4-intelligence-engine

## Context

E4 needs a supervised model producing a 0–100 collectability score (RF-02.1), a High/Medium/Low
category (RF-02.2), and **a plain-language explanation of the top factors behind each individual
score** (RF-02.3).

The backend currently has no ML library — `numpy==2.2.1` and `pandas==2.2.3` only. Adding one is
an architectural decision.

The explanation requirement is the binding constraint. It is per-prediction, not global: the
operator must see why *this* client scored 34, not which features matter on average.

## Decision

**Add `scikit-learn` and use `LogisticRegression`, trained on demand per scenario.**

Score: `predict_proba(X)[:, 1] * 100`.

Explanation (s4.4): `contribution_i = coef_i × (x_i − mean_i)`, ranked, top 3 surfaced. Linear
models give exact per-prediction attribution arithmetically — no additional library, no
approximation.

**No model artifact is persisted.** The model is fit on the active scenario's own data each time
scoring runs.

## Alternatives considered

### Gradient boosting (`GradientBoostingClassifier`)

Would likely score better on tabular data.

Rejected. `feature_importances_` is global, so per-prediction attribution requires SHAP — a
second dependency, materially slower, and producing explanations that are harder to defend to a
non-technical audience. The epic's value is an *explainable* score; accuracy that costs
explainability is the wrong trade for this product.

### Hand-rolled logistic regression in numpy

No new dependency, nothing hidden.

Rejected. It reinvents a solved problem and puts the effort into gradient descent, convergence
and scaling — code a library already gets right — rather than into the demo. The failure mode
is subtle numerical bugs that pass tests and produce quietly wrong scores.

### Persisting a trained model artifact (joblib)

Closer to a production pattern.

Rejected for this epic. Scenarios hold 10–500 clients, so training is sub-second; caching buys
nothing measurable. Persistence would add artifact storage, versioning, staleness handling, and
an ambiguity about which scenario a stored model was trained on — real complexity for a
demonstrative asset. Revisit if scenario sizes grow by orders of magnitude.

## Consequences

**Positive**

- Per-score explanations are exact and cheap, satisfying RF-02.3 without a second dependency.
- Coefficients are inspectable, so the model's behaviour can be sanity-checked directly against
  the causal structure ADR-004 established (e.g. `days_overdue_max` should carry a negative
  coefficient; if it does not, something is wrong upstream).
- Scores always correspond to the scenario being viewed — no stale-artifact class of bug.

**Negative**

- `scikit-learn` pulls in `scipy`, adding ~60 MB to the backend image. Acceptable for a
  demonstrative asset; worth noting for deployment.
- Logistic regression assumes a roughly linear log-odds relationship. If evaluation shows it
  materially underperforms the naive baseline, revisit — but change the ADR rather than quietly
  swapping the model.
- Training on every scoring run is wasted work at larger scenario sizes.

**Neutral**

- Model access sits behind `IScoringPort`, so the implementation can be replaced without touching
  use cases — the same guardrail that keeps the backend provider-agnostic for LLMs.

---

## Amendment 1: regularization strength (2026-07-21, s4.3 T5)

**`LogisticRegression(C=0.01)`, not the default `C=1.0`.**

### What forced the amendment

s4.3's integration test asserted the epic design's canary — `days_overdue_max` must carry a
negative coefficient. On real generated data at n=1000 it came out **positive (+0.526)**: a model
stating that being further overdue makes a client *more* collectable.

The original ADR assumed coefficient attribution would be straightforward because the model is
linear. It is linear; the *features* are not independent.

| Feature pair | Correlation |
|---|---:|
| `days_overdue_max` ↔ `days_overdue_mean` | **0.872** |
| `days_overdue_max` ↔ `pct_invoices_settled` | −0.413 |

With collinear predictors the fit splits their weight arbitrarily, and the split moves with the
seed. Measured at `C=1.0`: **19 of 27 configurations** produced a wrong-signed coefficient on
`days_overdue_max`. Univariate correlations with the label were correct throughout (−0.283), so
the data and the labeller were sound — the *fit* was unstable, not the signal.

### Why it is not cosmetic

This ADR chose logistic regression **specifically** so s4.4 could explain each score by ranking
`coef × centred value`. Unstable signs make that explanation actively wrong: a collections manager
would be told that 78 days overdue *raised* the client's score. The model would rank acceptably
and explain nonsense — the failure mode hardest to catch by looking at accuracy.

### Decision

Set `C=0.01`. Stronger ridge shrinks correlated coefficients toward each other rather than letting
them trade off against one another.

Measured across 45 configurations (3 sectors × 3 sizes × 5 seeds):

| Setting | Wrong-signed coefficients | Mean ROC-AUC |
|---|---:|---:|
| `C=1.0` (default) | 19/27 | 0.716 |
| `C=0.1` | 4/27 | 0.725 |
| **`C=0.01`** | **0/45** | **~0.735** |
| Drop `days_overdue_mean`, `C=1.0` | 7/27 | 0.708 |

Regularization bought stability **and** improved mean AUC. Dropping the collinear feature was
considered and rejected: it discarded information and measured worse on both axes.

### Consequence for the quality gate

A single scenario's AUC carries real sampling noise — the measured per-run minimum is 0.577. The
gate is therefore two-part:

- **per-run floor 0.55** — catches a genuinely broken model
- **mean across seeds ≥ 0.65** — the actual quality signal (measured 0.732–0.739)

Evaluated on retail, the weakest sector, rather than a flattering one.

### Guard

`test_coefficient_signs_stable_across_seeds` fails if `C` returns to a value that reintroduces
sign instability. The constant carries its rationale inline in `sklearn_scorer.py`.
