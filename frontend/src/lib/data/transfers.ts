import "server-only";

import { serverFetch } from "@/lib/api";
import type { Transfer, TransferStatusHistoryEntry } from "@/types/api";

export async function listTransfers(): Promise<Transfer[]> {
  return serverFetch<Transfer[]>("/api/v1/transfers");
}

export async function getTransfer(transferId: string): Promise<Transfer> {
  return serverFetch<Transfer>(`/api/v1/transfers/${transferId}`);
}

export async function getTransferStatusHistory(transferId: string): Promise<TransferStatusHistoryEntry[]> {
  return serverFetch<TransferStatusHistoryEntry[]>(`/api/v1/transfers/${transferId}/status-history`);
}
