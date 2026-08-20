# Retrospective: E8 — Backlog Epic

**Closed:** 2026-08-20 · **Stories:** 1 (S8.14) · **Type:** administrative container

## What this epic actually was

E8 was not a planned delivery epic. It is a container that briefly held one item — S8.14 "PWA
Config", completed 2026-07-08 — during a period when work was being tracked outside the E1–E7
sequence. It has a `scope.md` listing a single story and no brief, no design, and no plan,
because none were produced.

## Disposition

**Superseded by E7 s7.1.** S8.14 and s7.1 address the same backlog item, B-14 (PWA
configuration). s7.1 is the real delivery: it completed the manifest (`id`, `scope`, `lang`,
maskable icon), hardened the service worker with versioned precache, stale-cache cleanup and a
locale-aware `/offline` fallback, recorded the decision as **ADR-010** (hand-rolled service
worker, no `next-pwa`), and removed the placeholder identity inherited from E1.

Whatever S8.14 delivered on 2026-07-08 was either absorbed or replaced by that work. The PWA
criterion is verified against s7.1's output, not S8.14's — see E7's retrospective.

## Why it is closed rather than deleted

The directory is kept because `scope.md` records that a PWA attempt existed a month before
s7.1, which is context for why s7.1's gemba found a placeholder identity to remove. Deleting it
would erase that.

## Lesson

Work tracked outside the epic sequence acquires an epic-shaped directory anyway, and then looks
like an open epic forever. E8 sat with an unchecked story box and no retrospective for six
weeks while being, in substance, finished and superseded. Either work belongs to a numbered
epic or it belongs in `work/backlog/` — the halfway state is what produced this.

**Status: CLOSED — superseded by E7 s7.1. No outstanding work.**
