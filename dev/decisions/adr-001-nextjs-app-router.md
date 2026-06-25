# ADR-001: Next.js 15 App Router for Frontend

**Date:** 2026-06-19  
**Status:** Accepted  
**Epic:** e1-project-scaffolding  

## Context

The project requires a modern frontend framework capable of serving a PWA with complex UI panels (Operations Panel and Executive Panel), server-side data fetching, and eventual internationalization. The choice at project start between the Next.js Pages Router (legacy, stable) and App Router (React Server Components, current) had downstream implications for routing conventions, data-fetching patterns, and shadcn/ui component compatibility.

## Decision

Use **Next.js 15 App Router** as the frontend architecture.

## Rationale

- App Router is the default and recommended path for new Next.js projects as of v13+; Pages Router is in maintenance mode.
- React Server Components allow co-locating data fetching with UI, reducing client bundle size — important for the Executive Panel's data-heavy KPI dashboard.
- `shadcn/ui` v4 targets App Router; its component primitives assume RSC-compatible import patterns.
- The team will avoid accumulating Pages Router debt that would require migration before production.

## Alternatives considered

| Alternative | Reason rejected |
|---|---|
| Next.js Pages Router | Legacy path; shadcn/ui v4 targets App Router; would require migration for any RSC features |
| Vite + React SPA | No built-in API routes; would require separate API gateway or CORS config to reach FastAPI; more setup overhead for a demo project |
| Remix | Smaller ecosystem for shadcn/ui; team unfamiliarity; no strong advantage over Next.js for this use case |

## Consequences

- **Easier:** SSR/SSG, API route handlers (`/app/api/*`), layout nesting, RSC patterns for data panels.
- **Harder:** Client component boundaries must be explicit (`"use client"` directive); file-based routing is strictly directory-mapped (PAT-5: `/api/*` URLs must live at `src/app/api/*/route.ts`).
- **Tooling:** ESLint flat config (`eslint.config.mjs`) required — `eslint-config-next` v9 dropped `.eslintrc.json` support (PAT-3).
- **WSL note:** npm operations must run on native ext4 filesystem, not `/mnt/c/` (PAT-4).

## Traces to

- PRD: Module 5 (Operations Panel), Module 6 (Executive Panel) — data-heavy, real-time panels benefit from RSC.
- CLAUDE.md: Technology stack (`Next.js 15, TypeScript, Tailwind CSS, shadcn/ui`).
