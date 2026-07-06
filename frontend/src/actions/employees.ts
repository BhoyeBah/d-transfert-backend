"use server";

import { revalidatePath } from "next/cache";

import { serverFetch } from "@/lib/api";
import { ApiError } from "@/lib/api-error";
import type { ActionState } from "@/lib/action-state";
import type { MutationResult } from "@/lib/mutation-result";
import { createEmployeeSchema } from "@/lib/validation/employees";
import type { Employee } from "@/types/api";

export async function createEmployeeAction(
  _prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const parsed = createEmployeeSchema.safeParse({
    full_name: formData.get("full_name"),
    phone: formData.get("phone"),
    password: formData.get("password"),
    permissions: formData.getAll("permissions"),
  });
  if (!parsed.success) {
    return { status: "error", fieldErrors: parsed.error.flatten().fieldErrors };
  }

  try {
    await serverFetch("/api/v1/employees", { method: "POST", body: parsed.data });
  } catch (error) {
    if (error instanceof ApiError) {
      return { status: "error", message: error.message };
    }
    return { status: "error", message: "Impossible de contacter le serveur." };
  }

  revalidatePath("/employees");
  return { status: "success" };
}

export async function updateEmployeePermissionsAction(
  employeeId: string,
  currentPermissions: string[],
  nextPermissions: string[]
): Promise<MutationResult<Employee>> {
  const grant = nextPermissions.filter((code) => !currentPermissions.includes(code));
  const revoke = currentPermissions.filter((code) => !nextPermissions.includes(code));

  try {
    const employee = await serverFetch<Employee>(`/api/v1/employees/${employeeId}/permissions`, {
      method: "PATCH",
      body: { grant, revoke },
    });
    revalidatePath("/employees");
    return { ok: true, data: employee };
  } catch (error) {
    if (error instanceof ApiError) {
      return { ok: false, message: error.message };
    }
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
}

export async function setEmployeeStatusAction(employeeId: string, isActive: boolean): Promise<MutationResult> {
  try {
    await serverFetch(`/api/v1/employees/${employeeId}/status`, {
      method: "PATCH",
      body: { is_active: isActive },
    });
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, message: error.message };
    return { ok: false, message: "Impossible de contacter le serveur." };
  }
  revalidatePath("/employees");
  return { ok: true, data: undefined };
}
