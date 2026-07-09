# Pull Board — E3: Synthetic Dataset Generator

Last updated: 2026-07-07  
Epic: logical container (no branch)  
Status: **Active** — authorized 2026-07-02 (Gustavo)

---

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|
| s3.1 | Procedural data generation layer | Rodrigo | in progress | No external deps — started 2026-07-02 |
| s3.2 | OpenRouter adapter | Nano | done | Implemented and tested |
| s3.3 | LLM enrichment layer | — | backlog | Depends on s3.1 (RawDataset) + s3.2 (ILLMPort) |
| s3.4 | Generate scenario endpoint & UI | — | backlog | Depends on s3.3 (use case complete) |

---

## Execution order

```
s3.1 ─┐
       ├─► s3.3 ─► s3.4
s3.2 ─┘
```

s3.1 and s3.2 can be developed in parallel.
