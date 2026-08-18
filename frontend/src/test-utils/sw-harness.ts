/**
 * Executes `public/sw.js` in a `node:vm` context with a stubbed Service Worker
 * global scope, so the worker's behaviour can be asserted directly.
 *
 * The tests this replaces asserted on the worker's *source text*
 * (`expect(swContent).toContain("addEventListener('fetch'")`), which passed
 * against a fetch handler that returned without calling `respondWith`. A test
 * that can only see the shape of a thing cannot see that the thing is empty.
 */
import fs from 'fs'
import path from 'path'
import vm from 'vm'

export const ORIGIN = 'https://app.test'

/** Minimal stand-in for a `Response`. Only what the worker touches. */
export interface FakeResponse {
  url: string
  body: string
  /** Marks responses produced by the fake network rather than read from cache. */
  fromNetwork: boolean
}

export function makeResponse(url: string, body: string, fromNetwork = false): FakeResponse {
  return { url, body, fromNetwork }
}

interface FakeRequestInit {
  url: string
  method?: string
  mode?: 'navigate' | 'cors' | 'no-cors' | 'same-origin'
}

export interface FakeRequest {
  url: string
  method: string
  mode: string
}

export function makeRequest({ url, method = 'GET', mode = 'cors' }: FakeRequestInit): FakeRequest {
  return { url: url.startsWith('http') ? url : `${ORIGIN}${url}`, method, mode }
}

/** Stub Cache Storage. Keys are request URLs. */
class FakeCache {
  readonly entries = new Map<string, FakeResponse>()

  constructor(private readonly harness: SwHarness) {}

  async match(request: FakeRequest | string): Promise<FakeResponse | undefined> {
    return this.entries.get(keyOf(request))
  }

  async put(request: FakeRequest | string, response: FakeResponse): Promise<void> {
    this.entries.set(keyOf(request), response)
  }

  async addAll(urls: string[]): Promise<void> {
    // Real `addAll` is atomic: one rejected fetch rejects the whole call and
    // leaves the cache untouched. The harness models that, because a silently
    // disabled precache is the failure mode this worker is most exposed to.
    const fetched: Array<[string, FakeResponse]> = []
    for (const url of urls) {
      const response = await this.harness.network(makeRequest({ url }))
      // Stored copies are cache hits from here on, whatever their provenance —
      // this is what lets a test tell "served from cache" apart from
      // "served from the network".
      fetched.push([keyOf(url), { ...response, fromNetwork: false }])
    }
    for (const [key, response] of fetched) this.entries.set(key, response)
  }
}

function keyOf(request: FakeRequest | string): string {
  const url = typeof request === 'string' ? request : request.url
  return url.startsWith('http') ? url : `${ORIGIN}${url}`
}

export class SwHarness {
  readonly caches = new Map<string, FakeCache>()
  readonly deletedCaches: string[] = []
  readonly listeners = new Map<string, (event: unknown) => void>()

  skipWaitingCalled = false
  clientsClaimed = false
  /** When true the fake network rejects, simulating a dropped connection. */
  offline = false
  /** URLs the fake network was asked for, in order. */
  readonly requested: string[] = []

  async network(request: FakeRequest): Promise<FakeResponse> {
    this.requested.push(request.url)
    if (this.offline) throw new TypeError('Failed to fetch')
    return makeResponse(request.url, `network:${new URL(request.url).pathname}`, true)
  }

  /** Seeds a cache as if a previous worker version had populated it. */
  seedCache(name: string, entries: Record<string, string>): void {
    const cache = new FakeCache(this)
    for (const [url, body] of Object.entries(entries)) {
      cache.entries.set(keyOf(url), makeResponse(url, body))
    }
    this.caches.set(name, cache)
  }

  cacheNames(): string[] {
    return [...this.caches.keys()]
  }

  cacheEntries(name: string): string[] {
    return [...(this.caches.get(name)?.entries.keys() ?? [])]
  }

  /**
   * Dispatches a lifecycle event and awaits everything handed to `waitUntil`,
   * so assertions run after the worker has actually finished its work.
   */
  async dispatchLifecycle(type: 'install' | 'activate'): Promise<void> {
    const pending: Promise<unknown>[] = []
    const listener = this.listeners.get(type)
    if (!listener) throw new Error(`no ${type} listener registered`)
    listener({ waitUntil: (p: Promise<unknown>) => pending.push(p) })
    await Promise.all(pending)
  }

  /**
   * Dispatches a fetch event. Resolves to the response the worker provided, or
   * `undefined` when the worker declined to handle the request — which is the
   * assertion that matters for /api, non-GET and cross-origin traffic.
   */
  async dispatchFetch(init: FakeRequestInit): Promise<FakeResponse | undefined> {
    const listener = this.listeners.get('fetch')
    if (!listener) throw new Error('no fetch listener registered')

    let responded: Promise<FakeResponse> | undefined
    listener({
      request: makeRequest(init),
      respondWith: (p: Promise<FakeResponse>) => {
        responded = p
      },
      waitUntil: (p: Promise<unknown>) => p,
    })
    return responded ? await responded : undefined
  }

  /** Resolves after queued microtasks, so background revalidation lands. */
  async settle(): Promise<void> {
    await new Promise((resolve) => setTimeout(resolve, 0))
  }
}

export function loadServiceWorker(): SwHarness {
  const harness = new SwHarness()
  const swPath = path.resolve(__dirname, '../../public/sw.js')
  const source = fs.readFileSync(swPath, 'utf-8')

  const cacheStorage = {
    open: async (name: string) => {
      let cache = harness.caches.get(name)
      if (!cache) {
        cache = new FakeCache(harness)
        harness.caches.set(name, cache)
      }
      return cache
    },
    keys: async () => harness.cacheNames(),
    delete: async (name: string) => {
      harness.deletedCaches.push(name)
      return harness.caches.delete(name)
    },
    match: async (request: FakeRequest | string) => {
      for (const cache of harness.caches.values()) {
        const hit = await cache.match(request)
        if (hit) return hit
      }
      return undefined
    },
  }

  const self = {
    location: { origin: ORIGIN },
    addEventListener: (type: string, listener: (event: unknown) => void) => {
      harness.listeners.set(type, listener)
    },
    skipWaiting: () => {
      harness.skipWaitingCalled = true
      return Promise.resolve()
    },
    clients: {
      claim: () => {
        harness.clientsClaimed = true
        return Promise.resolve()
      },
    },
    caches: cacheStorage,
    fetch: (request: FakeRequest) => harness.network(request),
  }

  const context = vm.createContext({
    self,
    caches: cacheStorage,
    clients: self.clients,
    fetch: self.fetch,
    URL,
    Promise,
    console,
    setTimeout,
  })

  vm.runInContext(source, context, { filename: 'sw.js' })
  return harness
}
