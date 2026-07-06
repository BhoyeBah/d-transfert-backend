import type { Metadata } from "next";
import Link from "next/link";

import { listClients } from "@/lib/data/clients";
import { formatMoney } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CreateClientDialog } from "./create-client-dialog";

export const metadata: Metadata = { title: "Clients — D-Transfert" };

export default async function ClientsPage() {
  const clients = await listClients();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Clients"
        description="Clients avec un solde de dette suite à un manquant sur entrée."
        action={<CreateClientDialog />}
      />

      {clients.length === 0 ? (
        <EmptyState message="Aucun client enregistré." />
      ) : (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nom</TableHead>
                <TableHead>Téléphone</TableHead>
                <TableHead className="text-right">Solde (dette)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {clients.map((client) => (
                <TableRow key={client.id}>
                  <TableCell className="font-medium">
                    <Link href={`/clients/${client.id}`} className="hover:underline">
                      {client.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{client.phone}</TableCell>
                  <TableCell
                    className={`text-right font-medium tabular-nums ${
                      Number(client.balance) > 0 ? "text-destructive" : ""
                    }`}
                  >
                    {formatMoney(client.balance)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}
