import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  const isScenariosPage = pathname === "/scenarios"

  if (isScenariosPage) {
    return NextResponse.next()
  }

  const activeScenario = request.cookies.get("active_scenario_id")

  if (!activeScenario) {
    return NextResponse.redirect(new URL("/scenarios", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
}