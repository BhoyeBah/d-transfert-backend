"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { ActionState } from "@/lib/action-state";
import { createClientSchema } from "@/lib/validation/clients";

export async function createClientAction(_prevState: ActionState, formData: FormData): Promise<ActionState> {
  const parsed = createClientSchema.safeParse({
    name: formData.get("name"),
    phone: formData.get("phone"),
    note: formData.get("note"),
  });
  if (!parsed.success) {
    return { status: "error", fieldErrors: parsed.error.flatten().fieldErrors };
  }

  try {
    await serverFetch("/api/v1/clients", {
      method: "POST",
      body: { ...parsed.data, note: parsed.data.note || null },
    });
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "error", message: error.message };
    }
    return { status: "error", message: "Impossible de contacter le serveur." };
  }

  revalidatePath("/clients");
  return { status: "success" };
}
