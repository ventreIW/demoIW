# Next.js + Vitest TDD Patterns

Patterns discovered during s1.2 (Frontend Skeleton) implementation.

## vitest globals + TypeScript

**Problem:** `tsc --noEmit` fails with `Cannot find name 'it'` / `Cannot find name 'expect'` when using vitest globals in test files, even though vitest.config.ts has `globals: true`.

**Root cause:** vitest's `globals: true` only affects runtime — TypeScript's type checker doesn't pick up vitest's global type declarations unless explicitly configured.

**Fix:** Add `"types": ["vitest/globals"]` to `compilerOptions` in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "strict": true,
    "types": ["vitest/globals"],
    ...
  }
}
```

This tells TypeScript to include vitest's global type declarations (`describe`, `it`, `expect`, `beforeEach`, etc.) during type checking.

## Next.js App Router Route Handler TDD

**Problem:** ESLint `@typescript-eslint/no-unused-vars` flags `_request` when a route handler accepts a `Request` parameter but doesn't use it:

```typescript
// ESLint error: '_request' is defined but never used
export function GET(_request: Request) {
  return NextResponse.json({ status: "ok" })
}
```

**Fix:** Next.js App Router does not require route handlers to declare the `Request` parameter. Omit it entirely for handlers that don't need it:

```typescript
// Clean — no unused variables
export function GET() {
  return NextResponse.json({ status: "ok" })
}
```

**Test:** Call `GET()` without arguments — Next.js supplies the request internally at runtime:

```typescript
import { GET } from "./route"

it("returns 200 with status ok", async () => {
  const res = await GET()  // no args needed
  expect(res.status).toBe(200)
  expect(await res.json()).toEqual({ status: "ok" })
})
```

This works because `NextResponse` does not require the `Request` object for JSON responses. If the handler needs request data (query params, body, headers), declare the parameter — the lint rule's `argsIgnorePattern: "^_"` may then be needed in the ESLint config.

## App Router API Route Location

**Problem:** Design documents may specify route files at `src/app/healthcheck/route.ts`, expecting them to respond at `/api/healthcheck`. But Next.js App Router maps `src/app/healthcheck/route.ts` to `GET /healthcheck`, not `GET /api/healthcheck`.

**Fix:** API routes MUST live under `src/app/api/` to match `/api/*` URLs:

| URL path | File location |
|----------|---------------|
| `/api/healthcheck` | `src/app/api/healthcheck/route.ts` |
| `/healthcheck` | `src/app/healthcheck/route.ts` |

During implementation, always verify the URL path in the acceptance criteria matches the filesystem path. If the design places a route incorrectly, move the file to the correct `api/` subdirectory and use `git mv` so Git tracks the rename.

## shadcn/ui v4 Init Quirks

**Problem:** `npx shadcn@latest init --defaults` may timeout during the dependency installation phase, but `components.json` is already written to disk and the init step is effectively complete.

**Fix:** After timeout:
1. Check if `components.json` exists — if yes, init succeeded
2. Run `npx shadcn@latest add <components> --yes` — this works independently
3. If `tsc --noEmit` fails with missing modules like `@base-ui/react` or `class-variance-authority`, install them manually:
   ```bash
   npm install @base-ui/react class-variance-authority
   ```

**v4 differences from design docs:** shadcn v4 defaults may differ from the design spec (e.g., style "base-nova" instead of "default", baseColor "neutral" instead of "slate"). These are cosmetic — accept the defaults and move on rather than fighting the init prompts.

## `toBeDisabled` not available in vitest + testing-library

**Problem:** `expect(button).toBeDisabled()` fails with `Invalid Chai property: toBeDisabled` when using vitest with `@testing-library/react` but without `@testing-library/jest-dom` matchers.

**Root cause:** `toBeDisabled` is a jest-dom matcher, not part of vitest or testing-library. It requires `@testing-library/jest-dom` and an explicit setup file.

**Quick fix (no new deps):** Check the native DOM property directly:

```typescript
const button = screen.getByRole("button")
expect((button as HTMLButtonElement).disabled).toBe(true)
```

**Proper fix (adds dep):** Install `@testing-library/jest-dom` and add a vitest setup file:

```bash
npm install -D @testing-library/jest-dom
```

```typescript
// vitest.config.ts
export default defineConfig({
  test: {
    setupFiles: ["./src/test-setup.ts"],
  },
})
```

```typescript
// src/test-setup.ts
import "@testing-library/jest-dom/vitest"
```

## `useRouter()` requires `vi.mock("next/navigation")` in tests

**Problem:** Components that call `useRouter()` from `next/navigation` fail in vitest with `invariant expected app router to be mounted`. The App Router context does not exist in jsdom.

**Fix:** Mock `next/navigation` before importing the component:

```typescript
import { vi } from "vitest"

// Vitest hoists vi.mock calls to the top of the file automatically
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

// Import the component AFTER the mock
import MyComponent from "../MyComponent"
```

If the component also uses `usePathname`, `useSearchParams`, or other navigation hooks, add them to the mock:

```typescript
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
  usePathname: () => "/scenarios",
  useSearchParams: () => new URLSearchParams(),
}))
```

## `getByText` fails with multiple matching elements

**Problem:** `screen.getByText("Activo")` throws `Found multiple elements with the text: Activo` when the rendered component has multiple elements containing the same text (e.g., a badge span AND a footer span both showing "Activo").

**Fix:** Use `getAllByText` and assert on the count or individual elements:

```typescript
const matches = screen.getAllByText("Activo")
expect(matches.length).toBeGreaterThanOrEqual(1)
```

Or be more specific with `within`:

```typescript
const footer = screen.getByRole("contentinfo") // or any container
expect(within(footer).getByText("Activo")).toBeDefined()
```

## WSL cross-filesystem: `tsc` not in PATH after `npm install`

**Problem:** On WSL with files on `/mnt/c/` (Windows filesystem), `npm run typecheck` fails with `sh: 1: tsc: not found` even after `npm install` completes. The `node_modules/.bin/tsc` symlink may be broken on cross-filesystem mounts.

**Fix:** Use the direct path to the TypeScript compiler:

```bash
node node_modules/typescript/bin/tsc --noEmit
```

This bypasses the `.bin` symlink and works reliably on WSL cross-filesystem mounts.

## WSL cross-filesystem: vitest/eslint/prettier timeout

**Problem:** On WSL with files on `/mnt/c/`, `vitest` takes 100-180s per run, and `eslint`/`prettier` may timeout entirely (300s+). This is caused by the Plan 9 filesystem driver's poor performance with many small files (node_modules).

**Workaround:** 
- vitest: Use `--no-coverage` and scope to specific test files to reduce startup time. Even with the slowness, vitest completes reliably in ~180s.
- eslint: Skip per-task lint gates on WSL. Run `tsc --noEmit` for type checking and rely on `node --check` for syntax validation. Run full lint at story close or in CI.
- prettier: Skip per-task format gates on WSL. Run at story close or in CI.

**Permanent fix:** Move the project to the native WSL filesystem (`/home/renor/`) instead of `/mnt/c/`. This eliminates the cross-filesystem overhead entirely.