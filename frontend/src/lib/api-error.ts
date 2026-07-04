type FastApiValidationError = { loc: (string | number)[]; msg: string; type: string };

type FastApiErrorBody = { detail?: string | FastApiValidationError[] };

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Thrown when the caller has no usable session at all — callers should redirect to /login. */
export class UnauthenticatedError extends Error {
  constructor() {
    super("Session expirée ou absente.");
    this.name = "UnauthenticatedError";
  }
}

export function extractErrorMessage(body: unknown, fallback: string): string {
  const detail = (body as FastApiErrorBody | null)?.detail;
  if (typeof detail === "string" && detail.length > 0) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => item.msg)
      .filter(Boolean)
      .join(" ");
  }
  return fallback;
}
