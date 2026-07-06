import "server-only";

import { serverFetch } from "@/lib/api";
import type {
  Collaboration,
  CollaborationRateHistoryEntry,
  CollaboratorBalance,
  PrivateRate,
} from "@/types/api";

export async function listCollaborations(): Promise<Collaboration[]> {
  return serverFetch<Collaboration[]>("/api/v1/collaborations");
}

export async function getCollaboration(collaborationId: string): Promise<Collaboration> {
  return serverFetch<Collaboration>(`/api/v1/collaborations/${collaborationId}`);
}

export async function getRateHistory(collaborationId: string): Promise<CollaborationRateHistoryEntry[]> {
  return serverFetch<CollaborationRateHistoryEntry[]>(`/api/v1/collaborations/${collaborationId}/rate-history`);
}

export async function getCollaboratorBalance(collaborationId: string): Promise<CollaboratorBalance> {
  return serverFetch<CollaboratorBalance>(`/api/v1/collaborations/${collaborationId}/balance`);
}

export async function listPrivateRates(): Promise<PrivateRate[]> {
  return serverFetch<PrivateRate[]>("/api/v1/private-rates");
}
