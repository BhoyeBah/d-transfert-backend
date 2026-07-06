import type { Metadata } from "next";

import { PlatformAdminOverview } from "@/components/platform-admin-overview";

export const metadata: Metadata = { title: "Admin plateforme — D-Transfert" };

export default function AdminPage() {
  return <PlatformAdminOverview />;
}
