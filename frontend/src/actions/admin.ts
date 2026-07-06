"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { MutationResult } from "@/lib/mutation-result";
import type { CompanyStatus } from "@/types/api";

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
  return { ok: true, data: undefined };
}
