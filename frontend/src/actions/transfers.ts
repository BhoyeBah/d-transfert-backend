"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { MutationResult } from "@/lib/mutation-result";
import { createTransferSchema, type CreateTransferFormValues } from "@/lib/validation/transfers";
import type { Transfer } from "@/types/api";

export async function createTransferAction(
  payload: CreateTransferFormValues
): Promise<MutationResult<Transfer>> {
  const parsed = createTransferSchema.safeParse(payload);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? "Formulaire invalide." };
  }

  try {
    const transfer = await serverFetch<Transfer>("/api/v1/transfers", {
      method: "POST",
      body: {
        collaboration_id: parsed.data.collaboration_id,
        entry_id: parsed.data.entry_id || null,
        amount: String(parsed.data.amount),
        currency: parsed.data.currency,
        beneficiary_name: parsed.data.beneficiary_name || null,
        beneficiary_phone: parsed.data.beneficiary_phone,
        send_mode: parsed.data.send_mode,
        note: parsed.data.note || null,
        client_name: parsed.data.client_name || null,
        client_phone: parsed.data.client_phone || null,
      },
    });
    revalidatePath("/transfers");
    return { ok: true, data: transfer };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
}

export async function approveTransferAction(transferId: string): Promise<MutationResult> {
  try {
    await serverFetch(`/api/v1/transfers/${transferId}/approve`, { method: "POST", body: {} });
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, message: error.message };
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath("/transfers");
  revalidatePath(`/transfers/${transferId}`);
  return { ok: true, data: undefined };
}

export async function rejectTransferAction(transferId: string, reason: string): Promise<MutationResult> {
  if (!reason.trim()) {
    return { ok: false, message: "Un motif de rejet est requis." };
  }
  try {
    await serverFetch(`/api/v1/transfers/${transferId}/reject`, {
      method: "POST",
      body: { reason },
    });
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, message: error.message };
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath("/transfers");
  revalidatePath(`/transfers/${transferId}`);
  return { ok: true, data: undefined };
}
