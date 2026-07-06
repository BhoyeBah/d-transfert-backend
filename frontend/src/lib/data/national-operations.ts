import "server-only";

import { serverFetch } from "@/lib/api";
import type { NationalOperation } from "@/types/api";

export async function listNationalOperations(): Promise<NationalOperation[]> {
  return serverFetch<NationalOperation[]>("/api/v1/national-operations");
}

export async function getNationalOperation(operationId: string): Promise<NationalOperation> {
  return serverFetch<NationalOperation>(`/api/v1/national-operations/${operationId}`);
}
