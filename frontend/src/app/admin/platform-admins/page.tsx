import type { Metadata } from "next";

import { listPlatformAdmins } from "@/lib/data/admin";
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
import { UserStatusActions } from "../companies/[companyId]/user-status-actions";
import { CreatePlatformAdminDialog } from "./create-platform-admin-dialog";

export const metadata: Metadata = { title: "Comptes Super Admin — Administration D-Transfert" };

export default async function AdminPlatformAdminsPage() {
  const admins = await listPlatformAdmins();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Comptes Super Admin"
        description="Comptes disposant d'un accès complet à l'administration de la plateforme."
        action={<CreatePlatformAdminDialog />}
      />

      <Card>
        <CardContent>
          {admins.length === 0 ? (
            <EmptyState message="Aucun compte Super Admin." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Matricule</TableHead>
                  <TableHead>Téléphone</TableHead>
                  <TableHead>Créé le</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {admins.map((admin) => (
                  <TableRow key={admin.id}>
                    <TableCell className="font-medium">{admin.full_name}</TableCell>
                    <TableCell className="font-mono text-xs">{admin.matricule}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{admin.phone}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatDate(admin.created_at)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={admin.is_active ? "active" : "inactive"} />
                    </TableCell>
                    <TableCell>
                      <UserStatusActions userId={admin.id} companyId={null} isActive={admin.is_active} />
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
