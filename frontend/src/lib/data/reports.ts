import "server-only";

import { serverFetch } from "@/lib/api";
import type { AuditLogEntry, DailyReport } from "@/types/api";

export async function getDailyReport(date?: string): Promise<DailyReport> {
  const query = date ? `?date=${date}` : "";
  return serverFetch<DailyReport>(`/api/v1/reports/daily${query}`);
}

export async function listAuditLogs(): Promise<AuditLogEntry[]> {
  return serverFetch<AuditLogEntry[]>("/api/v1/audit-logs");
}
