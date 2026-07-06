import type { Metadata } from "next";

import { listEntries } from "@/lib/data/entries";
import { listWallets } from "@/lib/data/wallets";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Card } from "@/components/ui/card";
import { CreateEntryDialog } from "./create-entry-dialog";
import { EntriesTable } from "./entries-table";

export const metadata: Metadata = { title: "Entrées — D-Transfert" };

export default async function EntriesPage() {
  const [entries, wallets] = await Promise.all([listEntries(), listWallets()]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Entrées"
        description="Argent reçu des clients, à transformer en envoi ou en paiement collaborateur."
        action={<CreateEntryDialog wallets={wallets} />}
      />

      {entries.length === 0 ? (
        <EmptyState message="Aucune entrée enregistrée." />
      ) : (
        <Card className="py-4">
          <EntriesTable entries={entries} />
        </Card>
      )}
    </div>
  );
}
