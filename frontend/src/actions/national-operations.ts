"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { MutationResult } from "@/lib/mutation-result";
import {
  createNationalOperationSchema,
  nationalOperationTypeEndpoint,
  type NationalOperationFormValues,
} from "@/lib/validation/national-operations";
import type { NationalOperation } from "@/types/api";

export async function createNationalOperationAction(
  type: keyof typeof nationalOperationTypeEndpoint,
  payload: NationalOperationFormValues
): Promise<MutationResult<NationalOperation>> {
  const parsed = createNationalOperationSchema.safeParse(payload);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? "Formulaire invalide." };
  }

  const lines = parsed.data.lines.map((line) => ({
    wallet_id: line.wallet_id,
    amount_in: line.direction === "in" ? String(line.amount) : "0",
    amount_out: line.direction === "out" ? String(line.amount) : "0",
    currency: line.currency,
    note: line.note || null,
  }));

  try {
    const operation = await serverFetch<NationalOperation>(
      `/api/v1/national-operations/${nationalOperationTypeEndpoint[type]}`,
      {
        method: "POST",
        body: {
          client_name: parsed.data.client_name || null,
          client_phone: parsed.data.client_phone || null,
          note: parsed.data.note || null,
          lines,
        },
      }
    );
    revalidatePath("/national-operations");
    return { ok: true, data: operation };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
}

export async function cancelNationalOperationAction(operationId: string): Promise<MutationResult> {
  try {
    await serverFetch(`/api/v1/national-operations/${operationId}/cancel`, { method: "POST" });
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath("/national-operations");
  revalidatePath(`/national-operations/${operationId}`);
  return { ok: true, data: undefined };
}
