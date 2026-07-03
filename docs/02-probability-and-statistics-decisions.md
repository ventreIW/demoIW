# Probability & Statistics Decisions

> How demoIW turns random numbers into a *realistic, learnable* book of overdue invoices — and
> every distributional assumption behind it, stated plainly. Written so a non-statistician can
> follow it and a statistician can audit it.
>
> Canonical decisions live in [ADR-003](../dev/decisions/adr-003-procedural-llm-hybrid.md) and
> [ADR-004](../dev/decisions/adr-004-pattern-driven-behavioral-model.md). This doc explains the
> *why* in one place.

---

## 1. The core idea: procedural + LLM hybrid

We generate data in **two layers** (ADR-003):

- **Procedural layer** (built, s3.1) — produces all the **numbers and structure** using classic
  statistical sampling: how many clients, how many invoices, how much they owe, how overdue they
  are, whether they paid. This layer is **deterministic and reproducible**.
- **LLM layer** (later, s3.3) — replaces only the **qualitative text** (company names, sector
  descriptions) with AI-written content, so the data reads authentically.

**Why split them?** A pure-AI generator can't guarantee statistical properties or exact counts,
and it isn't reproducible. Pure procedural data looks flat and templated. The hybrid gives us the
best of both: **hard statistical guarantees + believable prose.**

---

## 2. Reproducibility: same seed → same data

A demo must be repeatable. Every random choice is driven by a single **seed**:

| Mechanism | Purpose |
|-----------|---------|
| `numpy.random.default_rng(seed)` | All numeric draws (amounts, counts, dates) |
| `Faker.seed(seed)` | Placeholder company names |
| **UUIDs from the seeded RNG** (`rng.bytes(16)`) | Even record IDs are reproducible — we deliberately **do not** use `uuid.uuid4()`, which reads OS entropy and would break determinism |
| `reference_date` parameter | Anchors invoice ageing to a fixed "today" so a portfolio is identical even if generated on a different calendar day |

**Result:** the same parameters always produce a byte-for-byte identical dataset. This is verified
by a test that generates twice and asserts the tables are equal.

---

## 3. The distributions we assume

Each quantity is drawn from a named probability distribution chosen to match how real accounts
receivable behave.

| Quantity | Distribution | Parameter(s) | Why this shape |
|----------|--------------|--------------|----------------|
| Client's payment behaviour | **Categorical / Multinomial** | sector-specific weights | Clients fall into behaviour classes (on-time, slow, defaulter); proportions differ by sector |
| Invoices per client | **Poisson**(λ = `invoice_volume`) | mean invoices/client | Poisson is the standard model for "count of events in a period" — most clients near the mean, a few with many |
| Invoice amount | **Normal**(mean, std), floored at 100 | `amount_mean`, `amount_std` | Invoice sizes cluster around a typical value with symmetric spread; floor prevents nonsensical tiny/negative amounts |
| Days overdue / days late | **Exponential**(scale = `late_days_mean`) | per behaviour class | Lateness is "time until an event" — many slightly late, a long tail of very late. Exponential is the natural memoryless model |
| Is an invoice overdue? | **Bernoulli**(p = `overdue_prob`) | per behaviour class | A yes/no draw; the probability depends on the client's class (see §4) |
| Partial-payment fraction | **Uniform**(0.20, 0.60) | — | A partial payer covers "some but not most" of the balance; uniform keeps it simple and bounded |

> **Naming honesty:** an earlier draft called the lateness parameter `days_overdue_lambda`, implying
> a *rate* λ. But NumPy's `exponential(x)` treats `x` as the **scale = mean**, not the rate. We
> renamed it `late_days_mean` so the name matches the math. (Rate and mean are reciprocals:
> mean = 1/λ.)

---

## 4. The key decision: behaviour is *causal*, not decorative (ADR-004)

This is the most important statistical choice in the project.

**The trap we avoided.** In the first version, whether an invoice was overdue came from a single
*global* probability, **independent** of the client. So a client labelled "on-time" could have an
all-overdue portfolio, and a "defaulter" could look pristine. The behaviour label was **decorative
— it didn't influence anything.**

For a demo whose entire purpose is to show a **collectability scoring engine (E4)** working, that
is fatal: if the label doesn't predict the outcome, **there is no signal for the model to learn**,
and the scoring looks like noise.

**The fix.** Each behaviour class carries a *profile* that **drives** its clients' outcomes:

| Payment pattern | Overdue probability | Mean days late | When overdue, do they pay? |
|-----------------|:------------------:|:--------------:|----------------------------|
| ON_TIME | 0.05 | 3 | — (rarely overdue) |
| DELAYED_30 | 0.25 | 30 | not yet |
| DELAYED_60 | 0.45 | 60 | not yet |
| DELAYED_90_PLUS | 0.65 | 100 | not yet |
| PARTIAL | 0.60 | 50 | **partial payment (20–60%)** |
| DEFAULT | 0.90 | 160 | no |

Now the label **predicts** the outcome. Overdue propensity rises monotonically from ON_TIME to
DEFAULT — exactly the relationship a scoring model is meant to discover. Verified on a large sample:

```
ON_TIME 0.05  →  DELAYED_30 0.23  →  DELAYED_60 0.44  →  DELAYED_90+ 0.69  →  DEFAULT 0.85
```

---

## 5. Sector differences

Different sectors have different mixes of behaviour classes. These weights (each row is a
probability distribution that sums to 1.0) decide how likely a new client in that sector is to be
each type:

| Sector | ON_TIME | DELAYED_30 | DELAYED_60 | DELAYED_90+ | PARTIAL | DEFAULT |
|--------|:-------:|:----------:|:----------:|:-----------:|:-------:|:-------:|
| Manufacturing | 0.30 | 0.30 | 0.15 | 0.08 | 0.10 | 0.07 |
| Retail | 0.25 | 0.20 | 0.15 | 0.10 | 0.20 | 0.10 |
| Professional services | 0.45 | 0.20 | 0.10 | 0.05 | 0.15 | 0.05 |

So professional services skews healthier (more on-time), retail has more partial payers, etc.

---

## 6. Emergent behaviour (a feature, not a bug)

We deliberately **removed** any global "overdue rate" knob. A portfolio's overall overdue rate is
**not set directly** — it **emerges** from the sector's mix of behaviour classes multiplied by each
class's overdue probability. This is exactly how real receivables work: the headline overdue rate
is a *consequence* of who your customers are.

In practice a manufacturing portfolio lands around **~30% overdue** without us ever specifying it.

---

## 7. Keeping records internally consistent

Statistics alone can produce contradictory rows, so the generator enforces coherence:

- A **settled ("paid")** invoice always has exactly **one payment for the full amount**, dated on
  or before "today", with `days_overdue = 0`.
- An **overdue** invoice has `days_overdue ≥ 1` and a `due_date` in the past.
- A **partial payer's** overdue invoice carries a payment **below** the invoice amount (balance
  still outstanding); a **defaulter's** overdue invoice carries **no** payment.
- Every invoice has `issue_date < due_date` (net-30 terms), and no payment is dated in the future.

These are checked by tests, so the data never tells a self-contradicting story on screen.

---

## 8. Assumptions & limitations (read before quoting numbers to a client)

These are honest simplifications appropriate for a **demo asset** — not a calibrated risk model:

- **The profile numbers are hand-authored, not fitted to real data.** They are plausible and tuned
  to give clear separation between behaviour classes for demonstration. They are the **first thing
  to revisit** if a prospect wants sector-accurate figures.
- Only **two invoice states** exist: `paid` and `overdue` (no *disputed*, *written-off*, or
  *not-yet-due*).
- **One payment per invoice** (a single full or partial payment) — no instalment plans.
- **Invoice amounts are independent of behaviour class** — only overdue behaviour depends on the
  class. (A defaulter's invoices are the same size as an on-time client's.)
- **Net-30 terms are fixed** for all sectors.
- The Normal amount distribution is **floored at 100**, which slightly biases the sample mean
  upward (observed ~0.7% above target) — negligible for a demo.

All of these are single, well-marked places in the code (`_PATTERN_PROFILES`,
`_SECTOR_PATTERN_WEIGHTS`) and can be adjusted or extended in a later story.

---

## 9. How we verify all of this

Every claim above is guarded by an automated test (see
`backend/tests/adapters/test_procedural_generator.py`):

| What's checked | Test |
|----------------|------|
| Same seed → identical data | `test_determinism` |
| Exact client count | `test_client_count_matches_params` |
| No negative/zero amounts; mean on target | `test_amounts_positive`, `test_amount_mean_within_tolerance` |
| **Behaviour predicts overdue rate (monotonic)** | `test_pattern_drives_overdue_propensity` |
| Records are internally coherent | `test_days_overdue_coherent_with_status`, `test_dates_are_coherent` |
| Payments match settlement behaviour | `test_settled_invoice_has_full_payment`, `test_partial_payers_make_partial_payments_on_overdue`, `test_default_overdue_invoices_have_no_payment` |
| Sector mixes differ correctly | `test_sector_weighting_manufacturing_slower_than_retail` |

If any assumption drifts, a test fails — so this document and the code stay in sync.
