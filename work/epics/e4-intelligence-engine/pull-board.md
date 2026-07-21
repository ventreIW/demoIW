# Pull Board — E4: Intelligence Engine

Last updated: 2026-07-21 (post-merge of s4.2 and s4.3)  
Epic: logical container (no branch)  
Status: **Active** — authorized 2026-07-21 (Gustavo)

---

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|
| s4.1 | i18n foundation | — | done | Delivered out-of-band by `b15-i18n-setup`, merged 2026-07-08 |
| s4.2 | Feature engineering & training set | Rodrigo | **done** | Merged 2026-07-21 (PR #7). ADR-006 validated: observed rates within 0.002 of prediction. 58 tests |
| s4.3 | Collectability scoring model | Rodrigo | **done** | Merged 2026-07-21 (PR #8). **M1 GO** — ROC-AUC mean 0.732–0.739. ADR-007 amended: C=0.01 after the canary caught collinearity |
| s4.4 | Score explanation | Rodrigo | **done** | Merged 2026-07-21 (PR #10). Ageing grouped as one factor; phrasing direction-aware after reading real output. 43 tests |
| s4.5 — formula | Priority value + Pareto threshold | Rodrigo | **implemented** | T1-T3 done 2026-07-21; PR open. Contract pushed at 5d8980f so s4.5-API is unblocked |
| s4.5 — API | Prioritized-list endpoint | Nano | **ready** | Contract available at `5d8980f`: `PrioritizedPortfolio` + `ScoringRun.outstanding_by_client`. Note: `value_share` reaches 0.80 at ~58% of accounts, not 20% |
| s4.6 | Rescore-on-contact endpoint | Nano | **ready** | s4.3 merged |
| s4.7 | i18n completion (switcher + retrofit) | Renata | ready | No deps. **Now also carries the form minimum 10 → 200** (s4.3 measurement: n=100 gives AUC 0.286–1.000) |
| s4.8 | LLM enrichment verification | Rodrigo | **blocked** | ⛔ Needs `OPENROUTER_API_KEY` |
| s4.9 | Score persistence — `IScoreRepository` + adapter | Nano | ready | No deps — entity/ORM/mappers exist from E2. Extracted from s4.3 so Nano isn't idle |

---

## Execution order

```
Rodrigo   s4.2 ──────────→ s4.3 ──┬→ s4.4
                                  └→ s4.5-formula ──→ (hands to Nano)
Nano      s4.9 ───────────────────────────────────→ s4.5-API
                                   └→ s4.6
Renata    s4.7 ─────────────────────── independent throughout

s4.8 ── blocked on credential; also blocks E5 s5.4 and E6 s6.3
```

**M1 is a go/no-go.** If the model cannot beat a naive baseline on held-out clients, stop and
revise ADR-007 rather than building explanation and prioritization on top of it.

## Board rules

Update this file on **every** story state transition. E3's board sat stale from 2026-07-07 to
2026-07-20, showing stories as *backlog* and *in progress* that had already merged — it actively
misrepresented delivery for two weeks.
