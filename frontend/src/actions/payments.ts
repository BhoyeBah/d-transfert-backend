"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { MutationResult } from "@/lib/mutation-result";
import { createPaymentSchema, type CreatePaymentFormValues } from "@/lib/validation/payments";
import type { Payment } from "@/types/api";

export async function createPaymentAction(
  payload: CreatePaymentFormValues
): Promise<MutationResult<Payment>> {
  const parsed = createPaymentSchema.safeParse(payload);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? "Formulaire invalide." };
  }

  try {
    const payment = await serverFetch<Payment>("/api/v1/payments", {
      method: "POST",
      body: {
        collaboration_id: parsed.data.collaboration_id,
        entry_id: parsed.data.entry_id || null,
        wallet_id: parsed.data.wallet_id || null,
        amount: String(parsed.data.amount),
        currency: parsed.data.currency,
        client_name: parsed.data.client_name || null,
        client_phone: parsed.data.client_phone || null,
        note: parsed.data.note || null,
      },
    });
    revalidatePath("/payments");
    return { ok: true, data: payment };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
}

export async function approvePaymentAction(paymentId: string): Promise<MutationResult> {
  try {
    await serverFetch(`/api/v1/payments/${paymentId}/approve`, { method: "POST", body: {} });
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, message: error.message };
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath("/payments");
  revalidatePath(`/payments/${paymentId}`);
  return { ok: true, data: undefined };
}

export async function rejectPaymentAction(paymentId: string, reason: string): Promise<MutationResult> {
  if (!reason.trim()) {
    return { ok: false, message: "Un motif de rejet est requis." };
  }
  try {
    await serverFetch(`/api/v1/payments/${paymentId}/reject`, {
      method: "POST",
      body: { reason },
    });
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, message: error.message };
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath("/payments");
  revalidatePath(`/payments/${paymentId}`);
  return { ok: true, data: undefined };
}
