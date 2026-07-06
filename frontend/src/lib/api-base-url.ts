const LOCAL_API_BASE_URL = "http://127.0.0.1:8000";

export function getApiBaseUrl(): string {
  const configured = process.env.API_BASE_URL?.trim();
  if (configured) {
    return configured.replace(/\/$/, "");
  }

  if (process.env.NODE_ENV === "development") {
    return LOCAL_API_BASE_URL;
  }

  throw new Error(
    "API_BASE_URL n'est pas configurée. Renseigne l'URL du backend FastAPI dans Coolify."
  );
}
