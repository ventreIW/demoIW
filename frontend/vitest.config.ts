import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    // next-intl ships ESM that imports the bare specifier `next/navigation`.
    // Inlining it routes those imports through Vite's resolver (which adds the
    // `.js`), instead of Node's externalized-dep resolver that fails on the bare
    // path. Without this, any test importing a module that pulls in next-intl's
    // navigation (e.g. [locale]/layout) fails to collect.
    server: {
      deps: {
        inline: ['next-intl'],
      },
    },
    coverage: {
      provider: 'v8',
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
})
