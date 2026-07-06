import type { Metadata } from "next";
import Link from "next/link";

import { listCollaborations } from "@/lib/data/collaborations";
import { listEntries } from "@/lib/data/entries";
import { listTransfers } from "@/lib/data/transfers";
import { formatDate, formatMoney } from "@/lib/format";
import { sendModeLabels } from "@/lib/validation/transfers";
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
import { CreateTransferDialog } from "./create-transfer-dialog";

export const metadata: Metadata = { title: "Envois internationaux — D-Transfert" };

export default async function TransfersPage() {
  const [transfers, collaborations, entries] = await Promise.all([
    listTransfers(),
    listCollaborations(),
    listEntries(),
  ]);
  const acceptedCollaborations = collaborations.filter((c) => c.status === "accepted");

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Envois internationaux"
        description="Transferts vers un collaborateur, avec ou sans entrée associée."
        action={<CreateTransferDialog collaborations={acceptedCollaborations} entries={entries} />}
      />

      {transfers.length === 0 ? (
        <EmptyState message="Aucun envoi enregistré." />
      ) : (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Référence</TableHead>
                <TableHead>Bénéficiaire</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Montant</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transfers.map((transfer) => (
                <TableRow key={transfer.id}>
                  <TableCell className="font-mono text-xs">
                    <Link href={`/transfers/${transfer.id}`} className="hover:underline">
                      {transfer.reference}
                    </Link>
                  </TableCell>
                  <TableCell className="text-sm">
                    {transfer.beneficiary_name ?? transfer.beneficiary_phone}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {sendModeLabels[transfer.send_mode]}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={transfer.status} />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(transfer.amount, transfer.currency)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(transfer.created_at)}
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
