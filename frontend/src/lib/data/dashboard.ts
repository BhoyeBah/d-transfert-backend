import "server-only";

import { serverFetch } from "@/lib/api";
import type { DashboardResponse, NotificationItem } from "@/types/api";

export async function getDashboard(): Promise<DashboardResponse> {
  return serverFetch<DashboardResponse>("/api/v1/dashboard");
}

export async function listNotifications(): Promise<NotificationItem[]> {
  return serverFetch<NotificationItem[]>("/api/v1/notifications");
}
