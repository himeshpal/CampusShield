import { NextResponse, type NextRequest } from "next/server";

// Must match Settings.session_cookie in the backend.
const SESSION_COOKIE = "cs_session";

// Cheap gate only: no cookie -> login page. The backend still verifies the JWT on
// every API call, and the app redirects to /login if it ever answers 401.
export function proxy(request: NextRequest) {
  if (request.cookies.has(SESSION_COOKIE)) return NextResponse.next();

  const login = new URL("/login", request.url);
  const path = request.nextUrl.pathname;
  if (path !== "/") login.searchParams.set("next", path);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: [
    "/",
    "/dashboard/:path*",
    "/assets/:path*",
    "/scans/:path*",
    "/checklist/:path*",
    "/alerts/:path*",
    "/reports/:path*",
    "/settings/:path*",
  ],
};
