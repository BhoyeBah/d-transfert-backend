import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { getClient, listClientMovements } from "@/lib/data/clients";
import { formatDate, formatMoney } from "@/lib/format";
import { EmptyState } from "@/components/empty-state";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const metadata: Metadata = { title: "Détail client — D-Transfert" };

export default async function ClientDetailPage({ params }: { params: Promise<{ clientId: string }> }) {
  const { clientId } = await params;
  const [client, movements] = await Promise.all([getClient(clientId), listClientMovements(clientId)]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/clients"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeftIcon className="size-3.5" />
          Clients
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">{client.name}</h1>
            <p className="text-sm text-muted-foreground">{client.phone}</p>
          </div>
          <div className="text-right">
            <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Solde
            </span>
            <p
              className={`text-2xl font-semibold tabular-nums ${
                Number(client.balance) > 0 ? "text-destructive" : ""
              }`}
            >
              {formatMoney(client.balance)}
            </p>
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Mouvements de solde</CardTitle>
        </CardHeader>
        <CardContent>
          {movements.length === 0 ? (
            <EmptyState message="Aucun mouvement." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Source</TableHead>
                  <TableHead className="text-right">Variation</TableHead>
                  <TableHead className="text-right">Solde après</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {movements.map((movement) => (
                  <TableRow key={movement.id}>
                    <TableCell className="text-sm">{movement.source_type}</TableCell>
                    <TableCell
                      className={`text-right tabular-nums ${
                        Number(movement.delta) > 0 ? "text-destructive" : "text-success"
                      }`}
                    >
                      {formatMoney(movement.delta)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{formatMoney(movement.balance_after)}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(movement.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
