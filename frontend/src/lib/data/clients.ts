import "server-only";

import { serverFetch } from "@/lib/api";
import type { Client, ClientBalanceMovement } from "@/types/api";

export async function listClients(): Promise<Client[]> {
  return serverFetch<Client[]>("/api/v1/clients");
}

export async function getClient(clientId: string): Promise<Client> {
  return serverFetch<Client>(`/api/v1/clients/${clientId}`);
}

export async function listClientMovements(clientId: string): Promise<ClientBalanceMovement[]> {
  return serverFetch<ClientBalanceMovement[]>(`/api/v1/clients/${clientId}/movements`);
}
