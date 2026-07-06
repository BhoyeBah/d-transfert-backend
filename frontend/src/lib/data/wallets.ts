import "server-only";

import { serverFetch } from "@/lib/api";
import type { Wallet, WalletMovement } from "@/types/api";

export async function listWallets(): Promise<Wallet[]> {
  return serverFetch<Wallet[]>("/api/v1/wallets");
}

export async function getWallet(walletId: string): Promise<Wallet> {
  return serverFetch<Wallet>(`/api/v1/wallets/${walletId}`);
}

export async function listWalletMovements(walletId: string): Promise<WalletMovement[]> {
  return serverFetch<WalletMovement[]>(`/api/v1/wallets/${walletId}/movements`);
}
