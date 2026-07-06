import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { getWallet, listWalletMovements } from "@/lib/data/wallets";
import { formatDate, formatMoney } from "@/lib/format";
import { walletTypeLabels } from "@/lib/validation/wallets";
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
import { ToggleWalletStatusButton } from "./toggle-status-button";

export const metadata: Metadata = { title: "Détail wallet — D-Transfert" };

export default async function WalletDetailPage({
  params,
}: {
  params: Promise<{ walletId: string }>;
}) {
  const { walletId } = await params;
  const [wallet, movements] = await Promise.all([
    getWallet(walletId),
    listWalletMovements(walletId),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/wallets"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeftIcon className="size-3.5" />
          Wallets
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">{wallet.name}</h1>
            <p className="text-sm text-muted-foreground">
              {wallet.code} · {walletTypeLabels[wallet.type]}
            </p>
          </div>
          <ToggleWalletStatusButton walletId={wallet.id} status={wallet.status} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="py-4">
          <CardContent className="px-4">
            <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Solde
            </span>
            <p className="text-2xl font-semibold tabular-nums">
              {formatMoney(wallet.balance, wallet.currency)}
            </p>
          </CardContent>
        </Card>
        <Card className="py-4">
          <CardContent className="px-4">
            <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Statut
            </span>
            <div className="mt-1">
              <StatusBadge status={wallet.status} />
            </div>
          </CardContent>
        </Card>
        <Card className="py-4">
          <CardContent className="px-4">
            <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              Description
            </span>
            <p className="text-sm">{wallet.description ?? "—"}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Historique des mouvements</CardTitle>
        </CardHeader>
        <CardContent>
          {movements.length === 0 ? (
            <EmptyState message="Aucun mouvement enregistré." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Sens</TableHead>
                  <TableHead className="text-right">Montant</TableHead>
                  <TableHead className="text-right">Solde après</TableHead>
                  <TableHead>Note</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {movements.map((movement) => (
                  <TableRow key={movement.id}>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(movement.created_at)}
                    </TableCell>
                    <TableCell className="text-xs">{movement.source_type}</TableCell>
                    <TableCell
                      className={
                        movement.direction === "in"
                          ? "font-medium text-success"
                          : "font-medium text-destructive"
                      }
                    >
                      {movement.direction === "in" ? "Entrée" : "Sortie"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(movement.amount, movement.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(movement.balance_after, movement.currency)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {movement.note ?? "—"}
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
