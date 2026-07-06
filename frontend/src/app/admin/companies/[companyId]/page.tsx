import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeftIcon } from "lucide-react";

import { getAdminCompanyDetail, getAdminSubscription, listAdminCompanyUsers } from "@/lib/data/admin";
import { formatDate, formatMoney } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatTile } from "@/components/stat-tile";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CompanyStatusActions } from "../company-status-actions";
import { SubscriptionForm } from "./subscription-form";
import { UserStatusActions } from "./user-status-actions";

export const metadata: Metadata = { title: "Détail entreprise — Administration D-Transfert" };

export default async function AdminCompanyDetailPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  const [company, users, subscription] = await Promise.all([
    getAdminCompanyDetail(companyId),
    listAdminCompanyUsers(companyId),
    getAdminSubscription(companyId),
  ]);
  const balanceEntries = Object.entries(company.wallets_balance_by_currency);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
          <Link href="/admin/companies">
            <ArrowLeftIcon />
            Entreprises
          </Link>
        </Button>
        <PageHeader
          title={company.name}
          description={`${company.registration_code} · ${company.phone} · ${company.default_currency} · créée le ${formatDate(company.created_at)}`}
          action={
            <div className="flex items-center gap-3">
              <StatusBadge status={company.status} />
              <CompanyStatusActions companyId={company.id} status={company.status} />
            </div>
          }
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Utilisateurs" value={company.users_count} />
        <StatTile label="Wallets" value={company.wallets_count} />
        <StatTile label="Entrées" value={company.entries_count} />
        <StatTile
          label="Opérations / envois / paiements"
          value={`${company.national_operations_count} / ${company.transfers_count} / ${company.payments_count}`}
        />
      </div>

      {balanceEntries.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Solde des wallets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {balanceEntries.map(([currency, amount]) => (
                <div key={currency} className="text-lg font-semibold tabular-nums">
                  {formatMoney(amount, currency)}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Utilisateurs ({users.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nom</TableHead>
                <TableHead>Matricule</TableHead>
                <TableHead>Téléphone</TableHead>
                <TableHead>Rôle</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.full_name}</TableCell>
                  <TableCell className="font-mono text-xs">{user.matricule}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{user.phone}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {user.is_owner ? "Owner" : "Employé"}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={user.is_active ? "active" : "inactive"} />
                  </TableCell>
                  <TableCell>
                    <UserStatusActions userId={user.id} companyId={company.id} isActive={user.is_active} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Abonnement</CardTitle>
        </CardHeader>
        <CardContent>
          <SubscriptionForm companyId={company.id} subscription={subscription} />
        </CardContent>
      </Card>
    </div>
  );
}
