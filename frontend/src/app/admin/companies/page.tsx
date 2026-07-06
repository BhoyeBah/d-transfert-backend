import type { Metadata } from "next";
import Link from "next/link";

import { listAdminCompanies } from "@/lib/data/admin";
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
import { CompanyStatusActions } from "./company-status-actions";

export const metadata: Metadata = { title: "Entreprises — Administration D-Transfert" };

export default async function AdminCompaniesPage() {
  const companies = await listAdminCompanies();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Entreprises"
        description={`${companies.length} entreprise${companies.length > 1 ? "s" : ""} inscrite${companies.length > 1 ? "s" : ""} sur la plateforme.`}
      />

      <Card>
        <CardContent>
          {companies.length === 0 ? (
            <EmptyState message="Aucune entreprise inscrite." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom</TableHead>
                  <TableHead>Code d&apos;inscription</TableHead>
                  <TableHead>Téléphone</TableHead>
                  <TableHead>Devise par défaut</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {companies.map((company) => (
                  <TableRow key={company.id}>
                    <TableCell className="font-medium">
                      <Link href={`/admin/companies/${company.id}`} className="hover:underline">
                        {company.name}
                      </Link>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{company.registration_code}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{company.phone}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{company.default_currency}</TableCell>
                    <TableCell>
                      <StatusBadge status={company.status} />
                    </TableCell>
                    <TableCell>
                      <CompanyStatusActions companyId={company.id} status={company.status} />
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
