import { describe, it, expect, beforeEach } from 'vitest'
import { loadServiceWorker, ORIGIN, type SwHarness } from '@/test-utils/sw-harness'

const CACHE = 'demoiw-v1'

describe('sw.js', () => {
  let sw: SwHarness

  beforeEach(() => {
    sw = loadServiceWorker()
  })

  it('registers install, activate and fetch listeners', () => {
    expect([...sw.listeners.keys()].sort()).toEqual(['activate', 'fetch', 'install'])
  })

  describe('install', () => {
    it('precaches the offline pages, manifest and icons under the versioned cache', async () => {
      await sw.dispatchLifecycle('install')

      expect(sw.cacheNames()).toContain(CACHE)
      const cached = sw.cacheEntries(CACHE).map((url) => new URL(url).pathname)
      expect(cached).toEqual(
        expect.arrayContaining([
          '/offline',
          '/en/offline',
          '/manifest.json',
          '/icons/icon-192.png',
          '/icons/icon-512.png',
          '/icons/apple-touch-icon.png',
        ]),
      )
    })

    it('does not precache live app-shell routes, which would serve stale data', async () => {
      await sw.dispatchLifecycle('install')

      const cached = sw.cacheEntries(CACHE).map((url) => new URL(url).pathname)
      expect(cached).not.toContain('/')
      expect(cached).not.toContain('/cases')
      expect(cached).not.toContain('/executive')
    })

    it('calls skipWaiting so the new worker takes over without a second reload', async () => {
      await sw.dispatchLifecycle('install')
      expect(sw.skipWaitingCalled).toBe(true)
    })
  })

  describe('activate', () => {
    it('deletes caches from previous versions and keeps the current one', async () => {
      sw.seedCache('demoiw-v0', { '/offline': 'stale' })
      sw.seedCache(CACHE, { '/offline': 'current' })

      await sw.dispatchLifecycle('activate')

      expect(sw.deletedCaches).toEqual(['demoiw-v0'])
      expect(sw.cacheNames()).toContain(CACHE)
    })

    it('claims open clients', async () => {
      await sw.dispatchLifecycle('activate')
      expect(sw.clientsClaimed).toBe(true)
    })
  })

  describe('navigation requests', () => {
    beforeEach(async () => {
      await sw.dispatchLifecycle('install')
    })

    it('goes to the network first while online', async () => {
      const response = await sw.dispatchFetch({ url: '/cases', mode: 'navigate' })
      expect(response?.fromNetwork).toBe(true)
      expect(response?.body).toBe('network:/cases')
    })

    it('falls back to the Spanish offline page when the network fails', async () => {
      sw.offline = true
      const response = await sw.dispatchFetch({ url: '/cases', mode: 'navigate' })
      expect(response?.body).toBe('network:/offline')
    })

    it('falls back to the English offline page for /en routes', async () => {
      sw.offline = true
      const response = await sw.dispatchFetch({ url: '/en/cases', mode: 'navigate' })
      expect(response?.body).toBe('network:/en/offline')
    })

    it('treats the bare /en route as English', async () => {
      sw.offline = true
      const response = await sw.dispatchFetch({ url: '/en', mode: 'navigate' })
      expect(response?.body).toBe('network:/en/offline')
    })

    it('does not mistake a route merely starting with "en" for the English locale', async () => {
      sw.offline = true
      const response = await sw.dispatchFetch({ url: '/entregas', mode: 'navigate' })
      expect(response?.body).toBe('network:/offline')
    })
  })

  describe('static assets', () => {
    beforeEach(async () => {
      await sw.dispatchLifecycle('install')
    })

    it('serves a cached asset from the cache, not the network', async () => {
      const response = await sw.dispatchFetch({ url: '/icons/icon-192.png' })
      expect(response?.fromNetwork).toBe(false)
      expect(response?.body).toBe('network:/icons/icon-192.png')
    })

    it('revalidates a cached asset in the background', async () => {
      const url = `${ORIGIN}/icons/icon-192.png`
      const precacheHits = sw.requested.filter((requested) => requested === url).length

      await sw.dispatchFetch({ url: '/icons/icon-192.png' })
      await sw.settle()

      expect(sw.requested.filter((requested) => requested === url).length).toBe(precacheHits + 1)
    })

    it('falls through to the network for an asset that is not cached yet', async () => {
      const response = await sw.dispatchFetch({ url: '/_next/static/chunk.js' })
      expect(response?.fromNetwork).toBe(true)
    })
  })

  describe('requests the worker must not intercept', () => {
    beforeEach(async () => {
      await sw.dispatchLifecycle('install')
    })

    it('ignores API calls so the demo never shows cached business data', async () => {
      expect(await sw.dispatchFetch({ url: '/api/healthcheck' })).toBeUndefined()
    })

    it('ignores non-GET requests', async () => {
      expect(await sw.dispatchFetch({ url: '/api/cases', method: 'POST' })).toBeUndefined()
      expect(
        await sw.dispatchFetch({ url: '/scenarios', method: 'POST', mode: 'navigate' }),
      ).toBeUndefined()
    })

    it('ignores cross-origin requests', async () => {
      expect(
        await sw.dispatchFetch({ url: 'https://openrouter.ai/api/v1/chat', method: 'GET' }),
      ).toBeUndefined()
    })
  })
})
