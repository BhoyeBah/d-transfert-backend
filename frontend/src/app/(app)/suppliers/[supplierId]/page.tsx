import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { getSupplier, listSupplierMovements } from "@/lib/data/suppliers";
import { listWallets } from "@/lib/data/wallets";
import { formatDate, formatMoney } from "@/lib/format";
import { supplierMovementTypeLabels } from "@/lib/validation/suppliers";
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
import { RebalanceSupplierDialog } from "./rebalance-dialog";

export const metadata: Metadata = { title: "Détail fournisseur — D-Transfert" };

export default async function SupplierDetailPage({
  params,
}: {
  params: Promise<{ supplierId: string }>;
}) {
  const { supplierId } = await params;
  const [supplier, movements, wallets] = await Promise.all([
    getSupplier(supplierId),
    listSupplierMovements(supplierId),
    listWallets(),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/suppliers"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeftIcon className="size-3.5" />
          Fournisseurs
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">{supplier.name}</h1>
            <p className="text-sm text-muted-foreground">{supplier.code}</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
                Solde
              </span>
              <p className="text-2xl font-semibold tabular-nums">
                {formatMoney(supplier.balance, supplier.currency)}
              </p>
            </div>
            <RebalanceSupplierDialog supplierId={supplier.id} wallets={wallets} />
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Mouvements</CardTitle>
        </CardHeader>
        <CardContent>
          {movements.length === 0 ? (
            <EmptyState message="Aucun mouvement." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Référence</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Montant</TableHead>
                  <TableHead className="text-right">Solde après</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {movements.map((movement) => (
                  <TableRow key={movement.id}>
                    <TableCell className="font-mono text-xs">{movement.reference}</TableCell>
                    <TableCell>{supplierMovementTypeLabels[movement.type]}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(movement.amount, supplier.currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatMoney(movement.balance_after, supplier.currency)}
                    </TableCell>
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
