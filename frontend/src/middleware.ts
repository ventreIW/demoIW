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

  // Step 1: i18n routing (locale detection, redirect, rewrite)
  const response = i18nMiddleware(request)

  // Step 2: scenario redirect guard (after locale routing)
  // Strip locale prefix to check the actual route
  const pathWithoutLocale = pathname.replace(/^\/(en|es)(?=\/|$)/, '') || '/'

  // Allow scenarios page without active scenario cookie
  if (pathWithoutLocale === '/scenarios' || pathWithoutLocale.startsWith('/scenarios/')) {
    return response
  }

  // Guard: redirect to /scenarios if no active scenario
  const activeScenario = request.cookies.get('active_scenario_id')
  if (!activeScenario) {
    return NextResponse.redirect(new URL('/scenarios', request.url))
  }

  return response
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|manifest.json|sw.js|icons).*)'],
}