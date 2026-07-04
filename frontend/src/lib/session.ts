import "server-only";

import { cookies } from "next/headers";

import { decodeJwtPayload, type AccessTokenPayload } from "@/lib/jwt";

export const ACCESS_TOKEN_COOKIE = "dt_access_token";
export const REFRESH_TOKEN_COOKIE = "dt_refresh_token";

const isProduction = process.env.NODE_ENV === "production";

function cookieOptionsFor(token: string) {
  const payload = decodeJwtPayload(token);
  const maxAge = payload ? Math.max(payload.exp - Math.floor(Date.now() / 1000), 0) : undefined;
  return {
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax" as const,
    path: "/",
    ...(maxAge ? { maxAge } : {}),
  };
}

export async function setAuthCookies(accessToken: string, refreshToken: string) {
  const store = await cookies();
  store.set(ACCESS_TOKEN_COOKIE, accessToken, cookieOptionsFor(accessToken));
  store.set(REFRESH_TOKEN_COOKIE, refreshToken, cookieOptionsFor(refreshToken));
}

export async function clearAuthCookies() {
  const store = await cookies();
  store.delete(ACCESS_TOKEN_COOKIE);
  store.delete(REFRESH_TOKEN_COOKIE);
}

export async function getAccessToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(ACCESS_TOKEN_COOKIE)?.value;
}

export async function getRefreshToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(REFRESH_TOKEN_COOKIE)?.value;
}

export type Session = {
  userId: string;
  companyId: string | null;
  matricule: string | null;
  isOwner: boolean;
  isSuperAdmin: boolean;
};

function toSession(payload: AccessTokenPayload): Session {
  return {
    userId: payload.sub,
    companyId: payload.company_id,
    matricule: payload.matricule,
    isOwner: payload.is_owner,
    isSuperAdmin: payload.is_super_admin,
  };
}

/**
 * Optimistic session read from the access token cookie — sufficient for
 * layout/nav decisions (company name, role-based menu items). It does not
 * itself guarantee the token is still valid; every real data request still
 * goes through FastAPI, which is the actual source of truth.
 */
export async function getSession(): Promise<Session | null> {
  const token = await getAccessToken();
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  if (!payload) return null;
  return toSession(payload);
}
