# ADR-003: Procedural + LLM Hybrid for Synthetic Dataset Generation

**Date:** 2026-07-02
**Status:** Accepted
**Epic:** e3-synthetic-dataset-generator

## Context

E3 must generate realistic accounts-receivable portfolios (clients, invoices, payments)
on demand for demos. Two properties are in tension:

1. **Reproducibility** — a facilitator must be able to regenerate an identical dataset from
   the same parameters (repeatable demos, deterministic downstream scoring in E4).
2. **Qualitative realism** — company names and sector narratives must read as authentic, not
   like obvious placeholder data.

Pure-LLM generation gives (2) but not (1): LLM output is non-deterministic and cannot
guarantee statistical distributions (amounts, overdue rates, payment patterns). Pure
procedural generation gives (1) and statistical control but produces flat, templated
qualitative fields.

## Decision

Split generation into two layers:

- **s3.1 — procedural core (this story):** a seed-based `ProceduralGenerator` produces all
  **structural and statistical** data (client counts, invoice amounts ~ Normal, days-overdue
  ~ Exponential, sector-weighted payment patterns) as deterministic pandas DataFrames wrapped
  in a `RawDataset`. Determinism is anchored by `np.random.default_rng(seed)` for numeric
  draws and `Faker.seed(seed)` for placeholder names; UUIDs are drawn from the seeded RNG.
- **s3.3 — LLM enrichment (later):** an `ILLMPort` (OpenRouter, s3.2) replaces only the
  **qualitative** fields (company names, sector descriptions) on top of the deterministic base.

The procedural layer never calls the LLM; the LLM layer never invents structural/statistical data.

## Rationale

- **Determinism where it matters, creativity where it helps.** Statistics and identity stay
  reproducible; only cosmetic text varies with the LLM. Scoring (E4) consumes the stable
  numeric base regardless of enrichment.
- **Cost and latency.** Procedural generation is instant and free; LLM calls are reserved for
  the few qualitative fields, keeping the "Generar" flow within the ~30s epic target.
- **Testability.** The statistical core is unit-testable with tolerance assertions (no network,
  no flakiness). LLM enrichment can be tested/mocked independently behind its port.
- **Provider-agnostic.** LLM access is confined to `ILLMPort` per project guardrails — no
  coupling of the generation core to any provider.

## Alternatives considered

| Alternative | Reason rejected |
|---|---|
| Pure-LLM generation | Non-deterministic; cannot guarantee distributions or exact client counts; slow and costly at portfolio scale |
| Pure-procedural (Faker only, no LLM) | Reproducible but qualitative fields read as templated; fails the "not just Faker names" epic criterion |
| Deterministic-seeded LLM (temperature 0) | Still no distribution guarantees; determinism across provider/model versions is not contractual |

## Consequences

- **Easier:** s3.1 ships and is fully tested with zero external dependencies. Downstream
  scoring gets a stable, statistically-shaped input immediately.
- **Harder:** `RawDataset` must carry fields in a shape that survives LLM enrichment (s3.3
  overwrites `clients.name`) and later entity mapping (s3.4). Column contract is tracked as a
  design open question.
- **Boundary discipline:** pandas/numpy types are confined to the `dataset` adapter and
  `RawDataset` VO; they must not leak into domain entities (enforced by mapping at s3.4).

## Traces to

- E3 brief success criteria: "Reproducible generation", "Realistic distributions",
  "LLM enrichment runs (not just Faker names)".
- s3.1 design decisions D1–D5.
