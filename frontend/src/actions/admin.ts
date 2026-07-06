"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { ActionState } from "@/lib/action-state";
import type { MutationResult } from "@/lib/mutation-result";
import { createPlatformAdminSchema } from "@/lib/validation/admin";
import type { CompanyStatus, SubscriptionPlan, SubscriptionStatus } from "@/types/api";

export async function setAdminCompanyStatusAction(
  companyId: string,
  status: CompanyStatus
): Promise<MutationResult> {
  try {
    await serverFetch(`/api/v1/admin/companies/${companyId}/status`, {
      method: "PATCH",
      body: { status },
    });
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, message: error.message };
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath("/admin");
  revalidatePath("/admin/companies");
  revalidatePath(`/admin/companies/${companyId}`);
  return { ok: true, data: undefined };
}

export async function setAdminUserStatusAction(
  userId: string,
  companyId: string | null,
  isActive: boolean
): Promise<MutationResult> {
  try {
    await serverFetch(`/api/v1/admin/users/${userId}/status`, {
      method: "PATCH",
      body: { is_active: isActive },
    });
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, message: error.message };
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  if (companyId) {
    revalidatePath(`/admin/companies/${companyId}`);
  } else {
    revalidatePath("/admin/platform-admins");
  }
  return { ok: true, data: undefined };
}

export async function createPlatformAdminAction(
  _prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const parsed = createPlatformAdminSchema.safeParse({
    full_name: formData.get("full_name"),
    phone: formData.get("phone"),
    password: formData.get("password"),
  });
  if (!parsed.success) {
    return { status: "error", fieldErrors: parsed.error.flatten().fieldErrors };
  }

  try {
    await serverFetch("/api/v1/admin/platform-admins", {
      method: "POST",
      body: parsed.data,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "error", message: error.message };
    }
    return { status: "error", message: "Impossible de contacter le serveur." };
  }

  revalidatePath("/admin/platform-admins");
  return { status: "success" };
}

export async function updateAdminSettingsAction(payload: {
  supported_currencies: string[];
  max_transaction_amount: number | null;
  maintenance_mode: boolean;
}): Promise<MutationResult> {
  try {
    await serverFetch("/api/v1/admin/settings", {
      method: "PATCH",
      body: {
        supported_currencies: payload.supported_currencies,
        max_transaction_amount:
          payload.max_transaction_amount !== null ? String(payload.max_transaction_amount) : null,
        maintenance_mode: payload.maintenance_mode,
      },
    });
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, message: error.message };
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath("/admin/settings");
  return { ok: true, data: undefined };
}

export async function updateAdminSubscriptionAction(
  companyId: string,
  payload: {
    plan: SubscriptionPlan;
    status: SubscriptionStatus;
    price: number | null;
    currency: string | null;
  }
): Promise<MutationResult> {
  try {
    await serverFetch(`/api/v1/admin/companies/${companyId}/subscription`, {
      method: "PATCH",
      body: {
        plan: payload.plan,
        status: payload.status,
        price: payload.price !== null ? String(payload.price) : null,
        currency: payload.currency || null,
      },
    });
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, message: error.message };
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath(`/admin/companies/${companyId}`);
  return { ok: true, data: undefined };
}
