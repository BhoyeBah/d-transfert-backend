import { z } from "zod";

export const NATIONAL_OPERATION_TYPES = ["deposit", "withdrawal", "exchange", "rebalance"] as const;

export const nationalOperationTypeLabels: Record<(typeof NATIONAL_OPERATION_TYPES)[number], string> = {
  deposit: "Dépôt",
  withdrawal: "Retrait",
  exchange: "Échange",
  rebalance: "Rééquilibrage",
};

export const nationalOperationTypeEndpoint: Record<(typeof NATIONAL_OPERATION_TYPES)[number], string> = {
  deposit: "deposits",
  withdrawal: "withdrawals",
  exchange: "exchanges",
  rebalance: "rebalances",
};

export const nationalOperationLineSchema = z.object({
  wallet_id: z.string().min(1, "Wallet requis."),
  direction: z.enum(["in", "out"]),
  amount: z.number().gt(0, "Montant requis."),
  currency: z.string().min(3).max(8),
  note: z.string().max(255).optional(),
});

export const createNationalOperationSchema = z.object({
  client_name: z.string().max(255).optional(),
  client_phone: z.string().max(32).optional(),
  note: z.string().max(255).optional(),
  lines: z.array(nationalOperationLineSchema).min(2, "Au moins 2 lignes sont requises."),
});

export type NationalOperationFormValues = z.infer<typeof createNationalOperationSchema>;
