"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { MutationResult } from "@/lib/mutation-result";
import { createEntrySchema, type EntryFormValues } from "@/lib/validation/entries";
import type { Entry } from "@/types/api";

export async function createEntryAction(payload: EntryFormValues): Promise<MutationResult<Entry>> {
  const parsed = createEntrySchema.safeParse(payload);
  if (!parsed.success) {
    return { ok: false, message: parsed.error.issues[0]?.message ?? "Formulaire invalide." };
  }

  try {
    const entry = await serverFetch<Entry>("/api/v1/entries", {
      method: "POST",
      body: {
        client_name: parsed.data.client_name || null,
        client_phone: parsed.data.client_phone || null,
        note: parsed.data.note || null,
        lines: parsed.data.lines.map((line) => ({
          wallet_id: line.wallet_id,
          amount: String(line.amount),
          currency: line.currency,
          note: line.note || null,
        })),
      },
    });
    revalidatePath("/entries");
    return { ok: true, data: entry };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
}

export async function mergeEntriesAction(entryIds: string[], note?: string): Promise<MutationResult<Entry>> {
  try {
    const entry = await serverFetch<Entry>("/api/v1/entries/merge", {
      method: "POST",
      body: { entry_ids: entryIds, note: note || null },
    });
    revalidatePath("/entries");
    return { ok: true, data: entry };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
}

export async function cancelEntryAction(entryId: string): Promise<MutationResult> {
  try {
    await serverFetch(`/api/v1/entries/${entryId}/cancel`, { method: "POST" });
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath("/entries");
  revalidatePath(`/entries/${entryId}`);
  return { ok: true, data: undefined };
}
