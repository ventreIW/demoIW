# shadcn/ui v4 Init Patterns

> Reference for `rai-story-implement` — captured from s1.2 (June 2026)

## Version Surprise

`npx shadcn@latest` installs **v4.x** (4.11.0 as of June 2026), not v3. Key differences:

| Aspect | v3 (expected) | v4 (actual) |
|--------|--------------|-------------|
| Primitives | Radix UI | `@base-ui/react` |
| Init style | `--style default` | `--defaults` gives `base-nova` |
| Base color | slate, gray, zinc, neutral, stone | neutral is default |
| CSS variables | `--css-variables` flag | `cssVariables: true` in components.json |
| Deps installed | radix-ui/* packages | @base-ui/react, class-variance-authority |

## Init Command (Non-Interactive)

```bash
npx shadcn@latest init --defaults
# Writes components.json but may TIME OUT during dependency install (especially on WSL /mnt/c/)
# The config file IS written even if the install step times out
```

## Post-Init: Missing Deps

If init times out during `Installing dependencies`, these packages may be missing from `package.json`:

```bash
npm install @base-ui/react class-variance-authority
```

Also verify `tailwindcss`, `postcss`, `autoprefixer` are installed (they may be missing if this is a fresh Next.js project).

## Add Components

```bash
npx shadcn@latest add button card separator skeleton --yes
# --yes skips confirmation prompts
```

Generated components go to `src/components/ui/` (configured in `components.json` aliases).

## components.json (v4 Example)

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "base-nova",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/styles/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "iconLibrary": "lucide",
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

## Pitfalls

1. **Pin the version if v3 is required**: use `npx shadcn@3 init` instead of `@latest`
2. **`cn()` utility**: requires both `clsx` and `tailwind-merge` — install manually if not auto-added
3. **globals.css**: v4 init does NOT modify globals.css — CSS variables are handled differently from v3. The file stays with just `@tailwind` directives.
4. **Do NOT edit generated components**: files in `src/components/ui/` are managed by shadcn CLI