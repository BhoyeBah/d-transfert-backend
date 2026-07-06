import type { Metadata } from "next";
import Link from "next/link";

import { getCompanyMe } from "@/lib/data/company";
import { listCollaborations } from "@/lib/data/collaborations";
import { getMe } from "@/lib/data/me";
import { formatDate } from "@/lib/format";
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
import { RequestCollaborationDialog } from "./request-collaboration-dialog";

export const metadata: Metadata = { title: "Collaborations — D-Transfert" };

export default async function CollaborationsPage() {
  const [collaborations, company, me] = await Promise.all([
    listCollaborations(),
    getCompanyMe(),
    getMe(),
  ]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Collaborations"
        description="Entreprises partenaires pour les envois internationaux."
        action={<RequestCollaborationDialog defaultCurrency={company.default_currency} />}
      />

      {collaborations.length === 0 ? (
        <EmptyState message="Aucune collaboration pour le moment." />
      ) : (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rôle</TableHead>
                <TableHead>Devise</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Taux actuel</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {collaborations.map((collaboration) => (
                <TableRow key={collaboration.id}>
                  <TableCell>
                    <Link href={`/collaborations/${collaboration.id}`} className="hover:underline">
                      {collaboration.initiator_company_id === me.company_id ? "Initiateur" : "Sollicité"}
                    </Link>
                  </TableCell>
                  <TableCell>{collaboration.currency}</TableCell>
                  <TableCell>
                    <StatusBadge status={collaboration.status} />
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {collaboration.current_rate ?? "—"}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(collaboration.created_at)}
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
