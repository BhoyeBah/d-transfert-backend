import "server-only";

import { serverFetch } from "@/lib/api";

export type Me = {
  id: string;
  company_id: string | null;
  matricule: string;
  full_name: string;
  is_owner: boolean;
  is_super_admin: boolean;
  permissions: string[];
};

export async function getMe(): Promise<Me> {
  return serverFetch<Me>("/api/v1/auth/me");
}
