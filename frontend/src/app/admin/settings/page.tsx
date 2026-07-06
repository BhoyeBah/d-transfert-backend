import type { Metadata } from "next";

import { getAdminSettings } from "@/lib/data/admin";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { SettingsForm } from "./settings-form";

export const metadata: Metadata = { title: "Paramètres plateforme — Administration D-Transfert" };

export default async function AdminSettingsPage() {
  const settings = await getAdminSettings();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Paramètres plateforme"
        description="Paramètres globaux appliqués à l'ensemble des entreprises."
      />

      <Card>
        <CardContent>
          <SettingsForm settings={settings} />
        </CardContent>
      </Card>
    </div>
  );
}
