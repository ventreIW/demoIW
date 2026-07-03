# E4 Brief — Intelligence Engine (Scoring + Prioritization + i18n)

**Backlog source:** B-05, B-06, B-15
**Status:** Proposed — not yet authorized
**Estimated size:** L (~7–10 days)
**Branch model:** logical container; stories branch from `main` after E3 merges

---

## Goal

Turn a generated/loaded scenario (E3) into **actionable intelligence**. Every overdue account
receives a collectability score (0–100), a recoverability category (High / Medium / Low), and a
plain-language explanation of the top factors. A prioritization engine then combines score and
outstanding amount into a per-case priority value and applies a Pareto filter to surface the
subset of cases holding ~80% of the expected recoverable value.

This epic also establishes the **internationalization (i18n) foundation** as its first story, so
every UI built from here on (E5, E6) is Spanish-by-default and English-ready *by construction* —
avoiding a painful retrofit later. Only the full English translation *pass* is deferred (to E7).

The scoring model is trained on the **synthetic data from E3**, whose causal pattern→outcome
signal (ADR-004) is exactly what makes the portfolio learnable.

---

## Success criteria

| Criterion | Verifiable signal | RF |
|---|---|---|
| Accounts scored | Each overdue account has a 0–100 score persisted | RF-02.1 |
| Categorized | Each account labelled High / Medium / Low | RF-02.2 |
| Explainable | Each score carries a human-readable top-factors explanation | RF-02.3 |
| Trained on synthetic data | Model fit on E3-generated data; no real data | RF-02.4 |
| Rescore hook | An endpoint recomputes a score given a contact result (wired to UI in E5) | RF-02.5 |
| Priority value | `priority = f(score, outstanding_amount)` computed per case | RF-03.1 |
| Pareto filter | API returns the ~80%-of-value subset | RF-03.2 |
| Ordered, filterable list | Prioritized list available via API, sortable/filterable by amount, days overdue, category | RF-03.3–4 |
| i18n foundation | UI renders ES by default, EN switch wired (strings externalized) | NFR-03 |

---

## Stories

| ID | Title | Size | Notes |
|---|---|---|---|
| s4.1 | i18n foundation (ES default, EN-ready) | S | next-intl (or equiv); strings structure + locale switcher. No full EN copy yet (E7). No deps — can start immediately. |
| s4.2 | Feature engineering & training set | S | Derive features from scenario data (days overdue, amount, payment-history pattern, sector); build labelled training set from synthetic data |
| s4.3 | Collectability scoring model | M | Train supervised propensity model; output 0–100 score + High/Med/Low; persist `Score` entities |
| s4.4 | Score explanation | S | Top-factor / feature-contribution explanation per score |
| s4.5 | Prioritization engine | S | Priority-value formula + Pareto filter + sort/filter API |
| s4.6 | Rescore-on-contact endpoint | S | Recompute score for a case given a contact result; endpoint consumed by E5 |

---

## Execution order

```
s4.1 (i18n) ─── independent, parallelizable ───┐
                                               │
s4.2 → s4.3 ┬→ s4.4                             │
            ├→ s4.5                             │
            └→ s4.6                             │
```

s4.1 is pure infra and can run in parallel with the ML track. s4.3 (the model) is the riskiest
and gates s4.4/s4.5/s4.6.

## Dependencies

- **E3** — needs generated scenarios with clients/invoices/payments to score and train on.
- **E2** — `Score` domain entity already exists; reuse it (do not re-model).
- OpenRouter is **not** required here (scoring is local ML).

## Risks

- **Model realism vs. simplicity** — for a demo, a transparent model (logistic regression /
  gradient boosting on engineered features) is preferable to a heavyweight one; explanation
  (RF-02.3) is easier and the causal synthetic signal is simple enough to learn. Decide at design.
- **Label definition** — "recovered within horizon" must be derivable from the synthetic data;
  confirm the generator emits enough signal (it does: pattern-driven overdue/payment behaviour).

## Out of scope

- Displaying scores/lists in the UI (E5 operations panel)
- Communications (E5), executive KPIs / NL query (E6)
- Full English translation pass (E7)
