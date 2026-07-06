import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { getMe } from "@/lib/data/me";
import { getTransfer, getTransferStatusHistory } from "@/lib/data/transfers";
import { formatDate, formatMoney } from "@/lib/format";
import { sendModeLabels } from "@/lib/validation/transfers";
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
import { TransferDecisionButtons } from "./transfer-decision-buttons";

export const metadata: Metadata = { title: "Détail envoi — D-Transfert" };

export default async function TransferDetailPage({
  params,
}: {
  params: Promise<{ transferId: string }>;
}) {
  const { transferId } = await params;
  const [transfer, history, me] = await Promise.all([
    getTransfer(transferId),
    getTransferStatusHistory(transferId),
    getMe(),
  ]);

  const isCounterparty = transfer.company_id !== me.company_id;
  const canDecide = transfer.status === "pending" && isCounterparty;
  const canSeePrivateRate = transfer.company_id === me.company_id;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/transfers"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeftIcon className="size-3.5" />
          Envois internationaux
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-mono text-lg font-semibold tracking-tight">{transfer.reference}</h1>
            <p className="text-sm text-muted-foreground">
              {transfer.beneficiary_name ?? transfer.beneficiary_phone} · {formatDate(transfer.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={transfer.status} />
            {canDecide && <TransferDecisionButtons transferId={transfer.id} />}
          </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Détails</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Montant</span>
              <span className="font-medium tabular-nums">{formatMoney(transfer.amount, transfer.currency)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Montant converti</span>
              <span className="font-medium tabular-nums">{transfer.converted_amount}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Taux collaboratif utilisé</span>
              <span className="tabular-nums">{transfer.collaborative_rate_used}</span>
            </div>
            {canSeePrivateRate && transfer.private_rate_used && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Taux privé utilisé</span>
                <span className="tabular-nums">{transfer.private_rate_used}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-muted-foreground">Mode d&apos;envoi</span>
              <span>{sendModeLabels[transfer.send_mode]}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Bénéficiaire</span>
              <span>{transfer.beneficiary_phone}</span>
            </div>
            {transfer.client_debt_amount && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Dette client (manquant)</span>
                <span className="font-medium tabular-nums text-destructive">
                  {formatMoney(transfer.client_debt_amount, transfer.currency)}
                </span>
              </div>
            )}
            {transfer.rejection_reason && (
              <div className="mt-2 rounded-md bg-destructive/10 px-3 py-2 text-destructive">
                Motif de rejet : {transfer.rejection_reason}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Historique des statuts</CardTitle>
          </CardHeader>
          <CardContent>
            {history.length === 0 ? (
              <EmptyState message="Aucun historique." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>De</TableHead>
                    <TableHead>Vers</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell>{entry.old_status ? <StatusBadge status={entry.old_status} /> : "—"}</TableCell>
                      <TableCell>
                        <StatusBadge status={entry.new_status} />
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatDate(entry.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
