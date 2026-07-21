# Pull Board — E4: Intelligence Engine

Last updated: 2026-07-21  
Epic: logical container (no branch)  
Status: **Active** — authorized 2026-07-21 (Gustavo)

---

| Story | Title | Owner | State | Notes |
|---|---|---|---|---|
| s4.1 | i18n foundation | — | done | Delivered out-of-band by `b15-i18n-setup`, merged 2026-07-08 |
| s4.2 | Feature engineering & training set | Rodrigo | in progress | Started 2026-07-21. ADR-006 (prediction target) lands here |
| s4.3 | Collectability scoring model | Rodrigo | backlog | Depends on s4.2 |
| s4.4 | Score explanation | Rodrigo | backlog | Depends on s4.3 |
| s4.5 — formula | Priority value + Pareto threshold | Rodrigo | backlog | Depends on s4.3 |
| s4.5 — API | Prioritized-list endpoint | Nano | backlog | Depends on s4.5 formula agreed |
| s4.6 | Rescore-on-contact endpoint | Nano | backlog | Depends on s4.3 |
| s4.7 | i18n completion (switcher + retrofit) | Renata | ready | No deps — can start immediately |
| s4.8 | LLM enrichment verification | Rodrigo | **blocked** | ⛔ Needs `OPENROUTER_API_KEY` |

---

## Execution order

```
s4.7 (Renata) ──────────────────── independent, start immediately
s4.2 → s4.3 ┬→ s4.4
            ├→ s4.5 formula → s4.5 API (Nano)
            └→ s4.6 (Nano)

s4.8 ── blocked on credential, unblocks E5 s5.4 and E6 s6.3 too
```

## Board rules

Update this file on **every** story state transition. E3's board sat stale from 2026-07-07 to
2026-07-20, showing stories as *backlog* and *in progress* that had already merged — it actively
misrepresented delivery for two weeks.
