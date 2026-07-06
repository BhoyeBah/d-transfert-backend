import { z } from "zod";

import { PermissionCode } from "@/lib/permissions";

const permissionCodeValues = Object.values(PermissionCode) as [string, ...string[]];

export const createEmployeeSchema = z.object({
  full_name: z.string().min(2, "2 caractères minimum.").max(255),
  phone: z.string().min(6, "Numéro invalide.").max(32),
  password: z.string().min(8, "8 caractères minimum."),
  permissions: z.array(z.enum(permissionCodeValues)).default([]),
});
