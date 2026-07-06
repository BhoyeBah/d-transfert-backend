import type { Metadata } from "next";

import { listAdminSystemLogs } from "@/lib/data/admin";
import { formatDate } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const metadata: Metadata = { title: "Logs système — Administration D-Transfert" };

export default async function AdminSystemLogsPage() {
  const logs = await listAdminSystemLogs();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Logs système"
        description="Erreurs applicatives et événements de sécurité (tentatives de connexion, verrouillages), distincts du journal d'audit métier."
      />

      <Card>
        <CardContent>
          {logs.length === 0 ? (
            <EmptyState message="Aucun événement système enregistré." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Niveau</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Message</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>
                      <StatusBadge status={log.level} />
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{log.source}</TableCell>
                    <TableCell className="max-w-md truncate text-sm text-muted-foreground" title={log.message}>
                      {log.message}
                    </TableCell>
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
