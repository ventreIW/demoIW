# Pull Board — E2: Data Foundation

Last updated: 2026-07-02  
Epic: logical container (no branch)  
Status: **Closed** — 5/5 stories complete (retrospective 2026-07-01)

---

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|---|
| s2.1 | Domain schema & migrations | Rodrigo | done ✓ | Merged 2026-06-25 |
| s2.2 | Scenario management API | Rodrigo | done ✓ | Merged 2026-06-25 |
| s2.3 | Scenario selector UI | Renata | done ✓ | Merged before E2 close |
| s2.4 | CSV upload (frontend) | Renata | done ✓ | Merged before E2 close |
| s2.5 | CSV upload (backend) | Rodrigo | done ✓ | Merged before E2 close |

---

## Execution order

```
s2.1 → s2.2 → s2.3 ┐
              s2.2 → s2.4 (frontend) ┐
                     s2.5 (backend) ─┴─ (s2.3, s2.4, s2.5 in parallel after s2.2)
```
