import "server-only";

import { serverFetch } from "@/lib/api";
import type { Supplier, SupplierBalanceMovement } from "@/types/api";

export async function listSuppliers(): Promise<Supplier[]> {
  return serverFetch<Supplier[]>("/api/v1/suppliers");
}

export async function getSupplier(supplierId: string): Promise<Supplier> {
  return serverFetch<Supplier>(`/api/v1/suppliers/${supplierId}`);
}

export async function listSupplierMovements(supplierId: string): Promise<SupplierBalanceMovement[]> {
  return serverFetch<SupplierBalanceMovement[]>(`/api/v1/suppliers/${supplierId}/movements`);
}
