"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { ActionState } from "@/lib/action-state";
import type { MutationResult } from "@/lib/mutation-result";
import {
  createSupplierSchema,
  rebalanceSupplierSchema,
  type RebalanceSupplierFormValues,
} from "@/lib/validation/suppliers";
import type { SupplierBalanceMovement } from "@/types/api";

export async function createSupplierAction(
  _prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const parsed = createSupplierSchema.safeParse({
    name: formData.get("name"),
    code: formData.get("code"),
    phone: formData.get("phone"),
    address: formData.get("address"),
    currency: formData.get("currency"),
    initial_balance: formData.get("initial_balance"),
    note: formData.get("note"),
  });
  if (!parsed.success) {
    return { status: "error", fieldErrors: parsed.error.flatten().fieldErrors };
  }

  try {
    await serverFetch("/api/v1/suppliers", {
      method: "POST",
      body: {
        ...parsed.data,
        phone: parsed.data.phone || null,
        address: parsed.data.address || null,
        note: parsed.data.note || null,
        initial_balance: String(parsed.data.initial_balance),
      },
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "error", message: error.message };
    }
    return { status: "error", message: "Impossible de contacter le serveur." };
  }

  revalidatePath("/suppliers");
  return { status: "success" };
}

export async function rebalanceSupplierAction(
  supplierId: string,
  payload: RebalanceSupplierFormValues
): Promise<MutationResult<SupplierBalanceMovement>> {
  const parsed = rebalanceSupplierSchema.safeParse(payload);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? "Formulaire invalide." };
  }

  try {
    const movement = await serverFetch<SupplierBalanceMovement>(`/api/v1/suppliers/${supplierId}/rebalance`, {
      method: "POST",
      body: {
        type: parsed.data.type,
        amount: String(parsed.data.amount),
        wallet_id: parsed.data.wallet_id,
        note: parsed.data.note || null,
      },
    });
    revalidatePath("/suppliers");
    revalidatePath(`/suppliers/${supplierId}`);
    return { ok: true, data: movement };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
}
