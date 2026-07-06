import type { Metadata } from "next";
import Link from "next/link";

import { listCollaborations } from "@/lib/data/collaborations";
import { listEntries } from "@/lib/data/entries";
import { listPayments } from "@/lib/data/payments";
import { listWallets } from "@/lib/data/wallets";
import { formatDate, formatMoney } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CreatePaymentDialog } from "./create-payment-dialog";

export const metadata: Metadata = { title: "Paiements collaborateurs — D-Transfert" };

export default async function PaymentsPage() {
  const [payments, collaborations, entries, wallets] = await Promise.all([
    listPayments(),
    listCollaborations(),
    listEntries(),
    listWallets(),
  ]);
  const acceptedCollaborations = collaborations.filter((c) => c.status === "accepted");

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Paiements collaborateurs"
        description="Règlement d'une dette entre collaborateurs, via une entrée ou un wallet."
        action={
          <CreatePaymentDialog collaborations={acceptedCollaborations} entries={entries} wallets={wallets} />
        }
      />

      {payments.length === 0 ? (
        <EmptyState message="Aucun paiement enregistré." />
      ) : (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Référence</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Montant</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payments.map((payment) => (
                <TableRow key={payment.id}>
                  <TableCell className="font-mono text-xs">
                    <Link href={`/payments/${payment.id}`} className="hover:underline">
                      {payment.reference}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={payment.status} />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(payment.amount, payment.currency)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(payment.created_at)}
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
