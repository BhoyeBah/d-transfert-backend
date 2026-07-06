import { z } from "zod";

export const requestCollaborationSchema = z.object({
  target_matricule: z.string().min(1, "Matricule requis."),
  currency: z.string().min(3).max(8),
  initial_rate: z.coerce.number().gt(0, "Le taux doit être positif."),
  note: z.string().max(255).optional(),
});

export const proposeRateSchema = z.object({
  new_rate: z.coerce.number().gt(0, "Le taux doit être positif."),
  note: z.string().max(255).optional(),
});

export const createPrivateRateSchema = z.object({
  collaboration_id: z.string().optional(),
  country: z.string().max(64).optional(),
  currency: z.string().min(3).max(8),
  rate: z.coerce.number().gt(0, "Le taux doit être positif."),
});
