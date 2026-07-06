import "server-only";

import { serverFetch } from "@/lib/api";
import type { Entry } from "@/types/api";

export async function listEntries(): Promise<Entry[]> {
  return serverFetch<Entry[]>("/api/v1/entries");
}

export async function getEntry(entryId: string): Promise<Entry> {
  return serverFetch<Entry>(`/api/v1/entries/${entryId}`);
}
