import "server-only";

import { serverFetch } from "@/lib/api";
import type {
  AdminCompanyDetail,
  AdminPlatformStats,
  AdminUser,
  AuditLogEntry,
  CompanyMe,
  PlatformSettings,
  Subscription,
  SystemLogEntry,
} from "@/types/api";

export async function listAdminCompanies(): Promise<CompanyMe[]> {
  return serverFetch<CompanyMe[]>("/api/v1/admin/companies");
}

export async function listAdminAuditLogs(): Promise<AuditLogEntry[]> {
  return serverFetch<AuditLogEntry[]>("/api/v1/admin/audit-logs");
}

export async function getAdminStats(): Promise<AdminPlatformStats> {
  return serverFetch<AdminPlatformStats>("/api/v1/admin/stats");
}

export async function getAdminCompanyDetail(companyId: string): Promise<AdminCompanyDetail> {
  return serverFetch<AdminCompanyDetail>(`/api/v1/admin/companies/${companyId}`);
}

export async function listAdminCompanyUsers(companyId: string): Promise<AdminUser[]> {
  return serverFetch<AdminUser[]>(`/api/v1/admin/companies/${companyId}/users`);
}

export async function listAdminSystemLogs(): Promise<SystemLogEntry[]> {
  return serverFetch<SystemLogEntry[]>("/api/v1/admin/system-logs");
}

export async function getAdminSettings(): Promise<PlatformSettings> {
  return serverFetch<PlatformSettings>("/api/v1/admin/settings");
}

export async function getAdminSubscription(companyId: string): Promise<Subscription> {
  return serverFetch<Subscription>(`/api/v1/admin/companies/${companyId}/subscription`);
}

export async function listPlatformAdmins(): Promise<AdminUser[]> {
  return serverFetch<AdminUser[]>("/api/v1/admin/platform-admins");
}
