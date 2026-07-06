import type { Metadata } from "next";
import { DownloadIcon } from "lucide-react";

import { getDailyReport, listAuditLogs } from "@/lib/data/reports";
import { formatDate, formatMoney } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { StatTile } from "@/components/stat-tile";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const metadata: Metadata = { title: "Rapports — D-Transfert" };

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const params = await searchParams;
  const [report, auditLogs] = await Promise.all([getDailyReport(params.date), listAuditLogs()]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Rapports" description="Rapport journalier et journal d'audit de l'entreprise." />

      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Rapport journalier — {report.date}</CardTitle>
          <form className="flex items-center gap-2" method="get">
            <Input type="date" name="date" defaultValue={params.date ?? report.date} className="h-9 w-40" />
            <Button type="submit" variant="outline" size="sm">
              Afficher
            </Button>
            <Button type="button" variant="outline" size="sm" asChild>
              <a href={`/api/reports/daily/export${params.date ? `?date=${params.date}` : ""}`}>
                <DownloadIcon />
                Export CSV
              </a>
            </Button>
          </form>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Dépôts" value={report.deposits_count} />
            <StatTile label="Retraits" value={report.withdrawals_count} />
            <StatTile label="Échanges" value={report.exchanges_count} />
            <StatTile label="Rééquilibrages" value={report.rebalances_count} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatTile label="Entrées" value={report.entries_count} />
            <StatTile
              label="Envois créés / approuvés / rejetés"
              value={`${report.transfers_created_count} / ${report.transfers_approved_count} / ${report.transfers_rejected_count}`}
            />
            <StatTile
              label="Paiements créés / approuvés / rejetés"
              value={`${report.payments_created_count} / ${report.payments_approved_count} / ${report.payments_rejected_count}`}
            />
          </div>
          {Object.keys(report.entries_total_by_currency).length > 0 && (
            <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
              Total entrées :{" "}
              {Object.entries(report.entries_total_by_currency)
                .map(([currency, amount]) => formatMoney(amount, currency))
                .join(" · ")}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Journal d&apos;audit</CardTitle>
        </CardHeader>
        <CardContent>
          {auditLogs.length === 0 ? (
            <EmptyState message="Aucune action enregistrée." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Action</TableHead>
                  <TableHead>Entité</TableHead>
                  <TableHead>Note</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.slice(0, 100).map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-mono text-xs">{log.action}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{log.entity_type}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{log.note ?? "—"}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(log.created_at)}
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
