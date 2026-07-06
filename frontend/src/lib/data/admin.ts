import "server-only";

import { serverFetch } from "@/lib/api";
import type { AuditLogEntry, CompanyMe } from "@/types/api";

export async function listAdminCompanies(): Promise<CompanyMe[]> {
  return serverFetch<CompanyMe[]>("/api/v1/admin/companies");
}

export async function listAdminAuditLogs(): Promise<AuditLogEntry[]> {
  return serverFetch<AuditLogEntry[]>("/api/v1/admin/audit-logs");
}
