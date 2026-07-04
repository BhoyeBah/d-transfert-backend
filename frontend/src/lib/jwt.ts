export type AccessTokenPayload = {
  sub: string;
  company_id: string | null;
  matricule: string | null;
  is_owner: boolean;
  is_super_admin: boolean;
  type: "access" | "refresh";
  iat: number;
  exp: number;
  jti?: string;
};

/**
 * Decodes a JWT payload without verifying its signature. Verification always
 * happens server-side in FastAPI on every request — this is only used here to
 * read claims for cookie expiry and optimistic UI (e.g. showing the company
 * name before the first real API call resolves).
 */
export function decodeJwtPayload<T = AccessTokenPayload>(token: string): T | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const json = Buffer.from(padded, "base64").toString("utf-8");
    return JSON.parse(json) as T;
  } catch {
    return null;
  }
}
