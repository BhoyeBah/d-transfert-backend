import "server-only";

import { serverFetch } from "@/lib/api";
import type { CompanyMe } from "@/types/api";

export async function getCompanyMe(): Promise<CompanyMe> {
  return serverFetch<CompanyMe>("/api/v1/companies/me");
}
