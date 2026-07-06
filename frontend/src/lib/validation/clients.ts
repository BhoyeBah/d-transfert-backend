import { z } from "zod";

export const createClientSchema = z.object({
  name: z.string().min(2, "2 caractères minimum.").max(255),
  phone: z.string().min(1, "Téléphone requis.").max(32),
  note: z.string().max(255).optional(),
});
