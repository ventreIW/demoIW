# ADR-005: LLM Enrichment Batching Strategy

**Date:** 2026-07-09
**Status:** Accepted
**Epic:** e3-synthetic-dataset-generator

## Context

The LLMEnrichmentService must call an external language model (LLM) to enrich client records with sector-appropriate names and descriptions. Each enrichment request can handle a limited number of records due to:
- Token limits imposed by the LLM API (both input and output).
- Practical limits on prompt size to avoid excessive latency and cost.
- API rate limits that restrict the number of requests per minute.

Without batching, each client record would require a separate LLM call, leading to:
- Hundreds or thousands of API calls per dataset, quickly exhausting rate limits.
- Increased total latency due to sequential network round-trips.
- Higher cost per enrichment due to overhead per request.

Batching groups multiple client records into a single LLM prompt, reducing the number of API calls while staying within token limits.

## Decision

We will batch client records in groups of a configurable size (default 20) before sending to the LLM. The LLMEnrichmentService constructor accepts a batch_size parameter, allowing callers to tune the trade-off between API efficiency and fault granularity.

The batching algorithm:
1. Split the RawDataset's client DataFrame into consecutive chunks of size batch_size.
2. For each batch, construct a prompt using the externalized template, substituting {sector} (assumed homogeneous within a batch) and {count} (the batch size).
3. Call the LLM port's generate method once per batch.
4. If the LLM call succeeds and returns valid JSON matching the batch size, map the results back to the corresponding client rows.
5. If the LLM call fails (malformed JSON, ExternalServiceError, or length mismatch), fall back to preserving the original client data for that batch (graceful degradation).

## Alternatives considered

| Alternative | Reason rejected |
|---|---|
| No batching (batch_size=1) | Simple but inefficient; would exceed API rate limits and increase latency and cost disproportionately. |
| Dynamic batching based on token count | Attempts to maximise records per request by measuring token usage. Adds complexity (requires token estimation or a trial call) and variable latency; gain over fixed batching is modest given relatively uniform per-record prompt size. |
| Adaptive batching with retry on failure | Starts with a large batch and reduces size on failure. Complicates flow and may cause head-of-line blocking; fixed batching with per-batch fallback provides predictable performance. |

## Consequences

- **Easier:** API efficiency reduces the number of LLM calls from N to ceil(N / batch_size). For a typical dataset of 1000 clients and batch_size=20, this is 50 calls vs. 1000. Stays under typical LLM API rate limits (e.g., 60 requests/minute) without extra coordination. Each batch incurs roughly the same network overhead, making total enrichment time easy to estimate. A failure in one batch affects only that batch — other batches can still succeed, and the service gracefully degrades to original data for the failed batch.
- **Harder:** Holds multiple batches in memory during processing (each batch is limited in size). If the LLM API allows larger prompts, a fixed batch_size may leave capacity unused — the configurable batch_size mitigates this. The implementation assumes all records in a batch share the same sector (taken from the first record); if a batch crosses sector boundaries, the prompt may be slightly off-spec. In practice the dataset is often sorted or grouped by sector, and the impact is minimal. Future work could enforce sector-homogeneous batches if needed.

## Traces to

- E3 brief success criteria: "LLM enrichment runs (not just Faker names)", "Configurable batching for LLM calls".
- s3.3 design decisions: batching strategy, graceful degradation, externalised prompt template.
- RF-04.6: Externalized configuration (prompt template loading).
