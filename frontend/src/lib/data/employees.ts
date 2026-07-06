import "server-only";

import { serverFetch } from "@/lib/api";
import type { Employee } from "@/types/api";

export async function listEmployees(): Promise<Employee[]> {
  return serverFetch<Employee[]>("/api/v1/employees");
}
