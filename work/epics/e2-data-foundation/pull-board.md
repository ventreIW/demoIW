# Pull Board — E2: Data Foundation

Last updated: 2026-06-25  
Epic: logical container (no branch)  
Status: **Active** — started 2026-06-25

---

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|
| s2.1 | Domain schema & migrations | — | backlog | First — all others depend on schema |
| s2.2 | Scenario management API | — | backlog | Depends on s2.1 |
| s2.3 | Scenario selector UI | — | backlog | Depends on s2.2 (needs API) |
| s2.4 | CSV upload | — | backlog | Can start in parallel with s2.3 after s2.2 |

---

## Execution order

```
s2.1 → s2.2 → s2.3 ┐
              s2.2 → s2.4 ┘  (s2.3 and s2.4 in parallel)
```
