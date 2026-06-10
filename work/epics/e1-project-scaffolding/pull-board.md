# Pull Board — E1: Project Scaffolding & CI Baseline

Last updated: 2026-06-10  
Epic: logical container (no branch)  
Status: **Proposed** — pending authorization

---

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|
| s1.1 | Repository scaffold & CI pipeline | — | backlog | No dependencies |
| s1.2 | Frontend skeleton | — | backlog | Depends on s1.1 (configs must exist) |
| s1.3 | Backend skeleton | — | backlog | Depends on s1.1 (configs must exist); s1.2 and s1.3 can run in parallel |

---

## Execution order

```
s1.1 → s1.2 ┐
             ├─ both merge into e1 branch → E1 closes → merge to main
s1.1 → s1.3 ┘
```
