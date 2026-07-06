import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { getEntry } from "@/lib/data/entries";
import { formatDate, formatMoney } from "@/lib/format";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CancelEntryButton } from "./cancel-entry-button";

export const metadata: Metadata = { title: "Détail entrée — D-Transfert" };

const CANCELLABLE_STATUSES = new Set(["unallocated"]);

export default async function EntryDetailPage({ params }: { params: Promise<{ entryId: string }> }) {
  const { entryId } = await params;
  const entry = await getEntry(entryId);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/entries"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeftIcon className="size-3.5" />
          Entrées
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-mono text-lg font-semibold tracking-tight">{entry.reference}</h1>
            <p className="text-sm text-muted-foreground">
              {entry.client_name ?? "Client non renseigné"} · {formatDate(entry.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={entry.status} />
            {CANCELLABLE_STATUSES.has(entry.status) && !entry.merged_into_id && (
              <CancelEntryButton entryId={entry.id} />
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Lignes</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Wallet</TableHead>
                  <TableHead className="text-right">Montant</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entry.lines.map((line, index) => (
                  <TableRow key={index}>
                    <TableCell className="font-mono text-xs">{line.wallet_id.slice(0, 8)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(line.amount, line.currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Disponible</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.entries(entry.available_by_currency).length === 0 ? (
              <p className="text-sm text-muted-foreground">Aucun montant disponible.</p>
            ) : (
              <div className="flex flex-col gap-2">
                {Object.entries(entry.available_by_currency).map(([currency, amount]) => (
                  <div key={currency} className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{currency}</span>
                    <span className="font-medium tabular-nums">{formatMoney(amount, currency)}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Affectations</CardTitle>
        </CardHeader>
        <CardContent>
          {entry.allocations.length === 0 ? (
            <EmptyState message="Aucune affectation." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Référence</TableHead>
                  <TableHead className="text-right">Montant affecté</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entry.allocations.map((allocation, index) => (
                  <TableRow key={index}>
                    <TableCell>{allocation.target_type === "transfer" ? "Envoi" : "Paiement"}</TableCell>
                    <TableCell className="font-mono text-xs">{allocation.target_id.slice(0, 8)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(allocation.amount_allocated, allocation.currency)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(allocation.created_at)}
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
