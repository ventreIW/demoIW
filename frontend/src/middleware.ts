import createMiddleware from 'next-intl/middleware'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { routing } from '@/i18n/routing'

const i18nMiddleware = createMiddleware(routing)

export default async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Skip middleware for static assets and API routes
  if (
    pathname.startsWith('/api/') ||
    pathname.startsWith('/_next/') ||
    pathname === '/favicon.ico' ||
    pathname === '/manifest.json' ||
    pathname === '/sw.js' ||
    pathname.startsWith('/icons/')
  ) {
    return NextResponse.next()
  }

  // i18n routing (locale detection, redirect, rewrite)
  //
  // There was an `active_scenario_id` cookie guard here that redirected every
  // non-/scenarios route back to /scenarios. Nothing in the app ever *set* that
  // cookie — it was only ever read — so the guard fired unconditionally and made
  // every operator route permanently unreachable. It went unnoticed because the
  // sidebar's only real link was /scenarios itself; s5.1 is the first story to add
  // a second route (and s5.2–s5.5 add more).
  //
  // The guard is not reinstated with a working cookie because the backend's
  // persisted scenario `status` is the durable truth (a cookie is per-browser), and
  // the pages already handle "no active scenario" with an explanatory message rather
  // than a silent redirect that leaves the operator wondering where they went.
  return i18nMiddleware(request)
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|manifest.json|sw.js|icons).*)'],
}
