# ADR-010 — Hand-rolled service worker instead of next-pwa

**Status:** Accepted
**Date:** 2026-08-18
**Story:** s7.1 (E7 — Demo Readiness)
**Deciders:** Rodrigo, Rai

## Context

Backlog item **B-14** specifies the PWA work as "next-pwa config, manifest, service worker". That
wording was written during E1 scaffolding, before the project settled on Next.js 15 with the App
Router (ADR-001).

Three things are true at the time of s7.1:

1. `next-pwa` (`shadowwalker/next-pwa`) has had no release supporting Next 15. It is webpack-only,
   and its build-time injection does not integrate cleanly with the App Router. Adopting it is a
   realistic build-failure risk, not a theoretical one.
2. The maintained successor is `@serwist/next`. It works with Next 15, but it introduces two
   dependencies and a build-time service-worker generation step whose output must itself be
   verified through `next build`.
3. `frontend/public/sw.js` and `frontend/public/manifest.json` already exist from E1. The worker is
   a stub — its `fetch` listener returns without calling `respondWith`, so nothing is cached — but
   the registration wiring in `[locale]/layout.tsx` and the `middleware.ts` matcher exclusions for
   `/sw.js`, `/manifest.json` and `/icons/` are already correct.

The demo requirement (NFR-04) is **installability plus graceful degradation when the network
drops**. It is not offline data access: the app reads live scenario, case, and KPI data from the
backend, and a cached dashboard would be actively misleading during a demo.

## Decision

Harden the existing hand-rolled `public/sw.js`. Do not add `next-pwa`, `@serwist/next`, Workbox, or
any other PWA build dependency.

The worker implements, in plain worker JavaScript with no build step:

- a versioned cache constant (`demoiw-v1`) with an app-shell precache on `install`
- deletion of every non-current cache on `activate`, followed by `clients.claim()`
- network-first for navigation requests, falling back to a precached, locale-aware `/offline` page
- stale-while-revalidate for same-origin static assets
- no interception of `/api/*`, non-GET, or cross-origin requests

## Consequences

**Positive**

- Zero new dependencies in a demonstrative asset, and no supply-chain surface added for it.
- The caching policy is legible in one ~60-line file rather than distributed across a plugin's
  configuration and generated output.
- The worker is directly unit-testable: `src/__tests__/pwa/sw.test.ts` loads it into a `node:vm`
  context with a stubbed Cache Storage API and executes its listeners. A generated worker would
  only be verifiable through a full build.
- No coupling to a plugin's Next.js version support, which is what made B-14's original choice
  stale in the first place.

**Negative**

- Workbox's battle-tested edge-case handling (range requests, navigation preload, precache
  integrity revisions) is not available. Accepted: none of it is exercised by the demo.
- The precache list is maintained by hand. If a precached URL 404s, `cache.addAll` fails atomically
  and the precache silently does nothing. Mitigated by restricting the list to assets certain to
  exist and by verifying cache contents in the browser during the s7.1 manual integration test.
- Cache busting is manual — shipping new precached assets requires bumping `CACHE_VERSION`.

**Neutral**

- B-14's "next-pwa" wording is now inaccurate. This ADR is the record; the backlog line is left as
  written since it is a historical artifact.

## Revisit when

Offline *functionality* enters scope — cached API responses, queued writes, or background sync. At
that point the hand-rolled worker stops being the simplest thing that works and `@serwist/next`
becomes the better trade. This ADR does not need revisiting merely to add another cached route.

## References

- ADR-001 — Next.js App Router
- `work/epics/e7-demo-readiness/stories/s7.1-design.md` § D1
- Backlog B-14, NFR-04
