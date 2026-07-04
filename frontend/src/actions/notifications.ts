"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";

export async function markNotificationReadAction(notificationId: string) {
  await serverFetch(`/api/v1/notifications/${notificationId}/read`, { method: "PATCH" });
  revalidatePath("/notifications");
  revalidatePath("/dashboard");
}
