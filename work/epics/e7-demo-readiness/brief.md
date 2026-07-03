# E7 Brief — Demo Readiness (PWA · Accessibility · EN · E2E)

**Backlog source:** B-14, B-16, B-15 (EN pass), NFR-05
**Status:** Proposed — not yet authorized
**Estimated size:** M (~4–6 days) — **the trimmable buffer**
**Branch model:** logical container; stories branch from `main` after E6 merges

---

## Goal

Make the whole product **demo-grade and presentable**: installable as a PWA, accessible
(WCAG 2.1 AA + keyboard navigation), fully bilingual (the English translation pass on top of the
ES-first foundation from E4), and validated end-to-end so the full <10-minute demo flow is proven
to work without assistance.

This epic is deliberately the **schedule buffer**: it is real polish, but if the timeline tightens
toward the Aug 14 deadline, its stories are what flex — the core demo (E4→E5→E6) still works
without them. Trim from the bottom of the story list if needed.

---

## Success criteria

| Criterion | Verifiable signal | RF |
|---|---|---|
| Installable PWA | App installs on Android and iOS; manifest + service worker present | NFR-04 |
| Accessible | WCAG 2.1 AA contrast met; all interactive elements keyboard-navigable | NFR-05 |
| Bilingual | Every UI string available in EN as well as ES | NFR-03 |
| Demo flow proven | Automated smoke test drives load-scenario → queue → case → comms → dashboard → NL query in < 10 min | NFR-01, B-16 |

---

## Stories

| ID | Title | Size | Notes |
|---|---|---|---|
| s7.1 | PWA configuration | XS | next-pwa config, manifest, service worker |
| s7.2 | Accessibility pass | S | WCAG 2.1 AA contrast audit + fixes; keyboard nav across all panels |
| s7.3 | English translation pass | S | Complete EN copy for all modules (builds on s4.1 i18n foundation) |
| s7.4 | End-to-end demo flow validation | S | Automated smoke test of the full 10-minute demo path |

---

## Execution order

```
s7.1 ─┐
s7.2 ─┤ (mostly independent)
s7.3 ─┘
        s7.4  ← last: validates the complete, polished flow
```

s7.1–s7.3 are largely independent and can be split across the team. s7.4 runs last because it
exercises everything.

## Dependencies

- **E4, E5, E6** — the full demo flow must exist before it can be polished and validated.
- **s4.1** — i18n foundation is the base for the s7.3 English pass.

## Trim guidance (if behind schedule)

Priority order to **keep**: s7.4 (proves the demo works) > s7.1 (PWA is a quick win and a visible
differentiator) > s7.2 (accessibility) > s7.3 (EN pass — droppable if the demo audience is
Spanish-speaking; move to parking lot). Decide with Gustavo at E6 close.

## Out of scope

- Production deployment / real-device store publishing (demo asset only)
- Real outbound message delivery, real authentication hardening
