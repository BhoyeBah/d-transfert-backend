import { NextResponse, type NextRequest } from "next/server";

import { decodeJwtPayload } from "@/lib/jwt";
import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE } from "@/lib/session";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

const PUBLIC_PATHS = ["/login", "/register", "/forgot-password", "/reset-password"];

const REFRESH_MARGIN_SECONDS = 60;

function isExpiredOrExpiringSoon(token: string | undefined): boolean {
  if (!token) return true;
  const payload = decodeJwtPayload(token);
  if (!payload) return true;
  return payload.exp - Math.floor(Date.now() / 1000) < REFRESH_MARGIN_SECONDS;
}

function isValid(token: string | undefined): boolean {
  if (!token) return false;
  const payload = decodeJwtPayload(token);
  if (!payload) return false;
  return payload.exp - Math.floor(Date.now() / 1000) > 0;
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublicPath = PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));

  let accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;

  let refreshedAccessToken: string | undefined;
  let refreshedRefreshToken: string | undefined;

  if (isExpiredOrExpiringSoon(accessToken) && isValid(refreshToken)) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
        cache: "no-store",
      });
      if (response.ok) {
        const data = (await response.json()) as { access_token: string; refresh_token: string };
        refreshedAccessToken = data.access_token;
        refreshedRefreshToken = data.refresh_token;
        accessToken = refreshedAccessToken;
      }
    } catch {
      // Backend unreachable: fall through, treated the same as "no valid session".
    }
  }

  const hasSession = isValid(accessToken);

  if (!isPublicPath && !hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    const response = NextResponse.redirect(loginUrl);
    response.cookies.delete(ACCESS_TOKEN_COOKIE);
    response.cookies.delete(REFRESH_TOKEN_COOKIE);
    return response;
  }

  if (isPublicPath && hasSession) {
    const payload = accessToken ? decodeJwtPayload(accessToken) : null;
    const landing = payload?.is_super_admin ? "/admin" : "/dashboard";
    return NextResponse.redirect(new URL(landing, request.url));
  }

  // Super Admin has no company_id: every company-scoped page (dashboard,
  // wallets, entries, ...) calls an endpoint that rejects it. Force it into
  // the platform-wide /admin section regardless of which URL it requests.
  if (hasSession && !isPublicPath && !pathname.startsWith("/admin")) {
    const payload = accessToken ? decodeJwtPayload(accessToken) : null;
    if (payload?.is_super_admin) {
      return NextResponse.redirect(new URL("/admin", request.url));
    }
  }

  const requestHeaders = new Headers(request.headers);
  if (refreshedAccessToken) {
    const forwardedCookie = requestHeaders.get("cookie") ?? "";
    requestHeaders.set(
      "cookie",
      forwardedCookie
        .split("; ")
        .filter((entry) => !entry.startsWith(`${ACCESS_TOKEN_COOKIE}=`))
        .concat(`${ACCESS_TOKEN_COOKIE}=${refreshedAccessToken}`)
        .join("; ")
    );
  }

  const response = NextResponse.next({ request: { headers: requestHeaders } });

  if (refreshedAccessToken && refreshedRefreshToken) {
    const accessPayload = decodeJwtPayload(refreshedAccessToken);
    const refreshPayload = decodeJwtPayload(refreshedRefreshToken);
    const now = Math.floor(Date.now() / 1000);
    response.cookies.set(ACCESS_TOKEN_COOKIE, refreshedAccessToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: accessPayload ? Math.max(accessPayload.exp - now, 0) : undefined,
    });
    response.cookies.set(REFRESH_TOKEN_COOKIE, refreshedRefreshToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: refreshPayload ? Math.max(refreshPayload.exp - now, 0) : undefined,
    });
  }

  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.svg$).*)"],
};
