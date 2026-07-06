import { z } from "zod";

export const entryLineSchema = z.object({
  wallet_id: z.string().min(1, "Wallet requis."),
  amount: z.number().gt(0, "Montant requis."),
  currency: z.string().min(3).max(8),
  note: z.string().max(255).optional(),
});

export const createEntrySchema = z.object({
  client_name: z.string().max(255).optional(),
  client_phone: z.string().max(32).optional(),
  note: z.string().max(255).optional(),
  lines: z.array(entryLineSchema).min(1, "Au moins une ligne est requise."),
});

export type EntryFormValues = z.infer<typeof createEntrySchema>;
