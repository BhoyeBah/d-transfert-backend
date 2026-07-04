import "server-only";

import { ApiError, UnauthenticatedError, extractErrorMessage } from "@/lib/api-error";
import { getAccessToken } from "@/lib/session";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  /** Set to true for the few endpoints callable without a session (register/login). */
  skipAuth?: boolean;
};

/**
 * Calls the FastAPI backend directly from the server (Server Components,
 * Server Actions, Route Handlers). Attaches the access token read from the
 * httpOnly cookie. Never called from the browser — the backend URL and the
 * token itself never reach client JavaScript.
 */
export async function serverFetch<T = unknown>(
  path: string,
  { body, skipAuth = false, headers, ...init }: RequestOptions = {}
): Promise<T> {
  const requestHeaders = new Headers(headers);
  requestHeaders.set("Content-Type", "application/json");

  if (!skipAuth) {
    const token = await getAccessToken();
    if (!token) {
      throw new UnauthenticatedError();
    }
    requestHeaders.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: requestHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json().catch(() => null) : await response.text();

  if (!response.ok) {
    if (response.status === 401 && !skipAuth) {
      throw new UnauthenticatedError();
    }
    throw new ApiError(response.status, extractErrorMessage(payload, "Une erreur est survenue."));
  }

  return payload as T;
}
