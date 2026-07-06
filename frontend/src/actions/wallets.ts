"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { ActionState } from "@/lib/action-state";
import { createWalletSchema } from "@/lib/validation/wallets";

export async function createWalletAction(_prevState: ActionState, formData: FormData): Promise<ActionState> {
  const parsed = createWalletSchema.safeParse({
    name: formData.get("name"),
    code: formData.get("code"),
    type: formData.get("type"),
    phone: formData.get("phone"),
    currency: formData.get("currency"),
    initial_balance: formData.get("initial_balance"),
    description: formData.get("description"),
  });

  if (!parsed.success) {
    return { status: "error", fieldErrors: parsed.error.flatten().fieldErrors };
  }

  try {
    await serverFetch("/api/v1/wallets", {
      method: "POST",
      body: {
        ...parsed.data,
        phone: parsed.data.phone || null,
        description: parsed.data.description || null,
        initial_balance: String(parsed.data.initial_balance),
      },
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "error", message: error.message };
    }
    return { status: "error", message: "Impossible de contacter le serveur." };
  }

  revalidatePath("/wallets");
  return { status: "success" };
}

export async function setWalletStatusAction(walletId: string, status: "active" | "inactive") {
  await serverFetch(`/api/v1/wallets/${walletId}/status`, {
    method: "PATCH",
    body: { status },
  });
  revalidatePath("/wallets");
  revalidatePath(`/wallets/${walletId}`);
}
