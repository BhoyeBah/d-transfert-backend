import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { getNationalOperation } from "@/lib/data/national-operations";
import { formatDate, formatMoney } from "@/lib/format";
import { nationalOperationTypeLabels } from "@/lib/validation/national-operations";
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
import { CancelOperationButton } from "./cancel-button";

export const metadata: Metadata = { title: "Détail opération — D-Transfert" };

export default async function NationalOperationDetailPage({
  params,
}: {
  params: Promise<{ operationId: string }>;
}) {
  const { operationId } = await params;
  const operation = await getNationalOperation(operationId);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link
          href="/national-operations"
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeftIcon className="size-3.5" />
          Opérations nationales
        </Link>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-mono text-lg font-semibold tracking-tight">{operation.reference}</h1>
            <p className="text-sm text-muted-foreground">
              {nationalOperationTypeLabels[operation.type as "deposit"] ?? operation.type} ·{" "}
              {formatDate(operation.created_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={operation.status} />
            {operation.status === "validated" && <CancelOperationButton operationId={operation.id} />}
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Lignes</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Wallet</TableHead>
                <TableHead className="text-right">Entrée</TableHead>
                <TableHead className="text-right">Sortie</TableHead>
                <TableHead className="text-right">Solde après</TableHead>
                <TableHead>Note</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operation.lines.map((line, index) => (
                <TableRow key={index}>
                  <TableCell className="font-mono text-xs">{line.wallet_id.slice(0, 8)}</TableCell>
                  <TableCell className="text-right tabular-nums text-success">
                    {Number(line.amount_in) > 0 ? formatMoney(line.amount_in, line.currency) : "—"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-destructive">
                    {Number(line.amount_out) > 0 ? formatMoney(line.amount_out, line.currency) : "—"}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {line.balance_after ? formatMoney(line.balance_after, line.currency) : "—"}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">{line.note ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
