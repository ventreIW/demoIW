# ADR-005: LLM Enrichment Batching Strategy (Summary)

**Date:** 2026-07-09  
**Status:** Accepted  
**Epic:** e3-synthetic-dataset-generator  

## Context
The LLMEnrichmentService must call an external language model (LLM) to enrich client records with sector-appropriate names and descriptions. Each enrichment request can handle a limited number of records due to token limits, prompt size constraints, and API rate limits. Without batching, each client would require a separate LLM call, quickly exhausting rate limits and increasing latency and cost.

## Decision
Batch client records in groups of a configurable size (default 20) before sending to the LLM. The LLMEnrichmentService constructor accepts a `batch_size` parameter to tune the trade‑off between API efficiency and fault granularity.

## Alternatives Considered
| Alternative | Reason rejected |
|---|---|
| No batching (batch_size=1) | Would exceed API rate limits and increase latency/cost disproportionately. |
| Dynamic token‑based batching | Adds complexity (requires token estimation) and variable latency; benefit over fixed batching is modest given uniform per‑record prompt size. |
| Adaptive batching with retry on failure | Complicates flow and can cause head‑of‑line blocking; fixed batching with per‑batch fallback offers predictable performance. |

## Consequences
- **Positive:** Reduces LLM calls from N to ceil(N/batch_size); stays within typical rate limits (e.g., 60 req/min); predictable latency; fault isolation (failure affects only one batch, graceful degradation to original data).
- **Negative:** Slightly higher memory usage; possible under‑utilization if the LLM allows larger prompts (mitigated by configurable batch_size); assumes sector homogeneity within a batch (usually acceptable as data is often sector‑sorted).

## Implementation Notes
- The batch_size is exposed via the LLMEnrichmentService constructor; default of 20 based on empirical testing with the OpenRouter API (~150 tokens per record, leaving room for ~30 records in a 4096‑token limit with a safety margin).
- Batching logic resides in `LLMEnrichmentService.enrich` and `_enrich_batch`, making the strategy easy to modify or replace.