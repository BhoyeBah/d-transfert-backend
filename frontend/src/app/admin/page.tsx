import type { Metadata } from "next";
import {
  BuildingIcon,
  FileClockIcon,
  ShieldXIcon,
  UsersIcon,
  WalletIcon,
  ActivityIcon,
} from "lucide-react";

import { getAdminStats } from "@/lib/data/admin";
import { formatMoney } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { StatTile } from "@/components/stat-tile";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = { title: "Administration plateforme — D-Transfert" };

export default async function AdminOverviewPage() {
  const stats = await getAdminStats();
  const volumeEntries = Object.entries(stats.volume_by_currency);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Vue d'ensemble"
        description="Indicateurs plateforme, tous comptes entreprises confondus."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Entreprises actives" value={stats.companies_active} icon={BuildingIcon} tone="success" />
        <StatTile
          label="Entreprises suspendues"
          value={stats.companies_suspended}
          icon={ShieldXIcon}
          tone={stats.companies_suspended > 0 ? "destructive" : "default"}
        />
        <StatTile label="Entreprises en attente" value={stats.companies_pending} icon={BuildingIcon} />
        <StatTile label="Total entreprises" value={stats.companies_total} icon={BuildingIcon} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Utilisateurs" value={stats.users_total} icon={UsersIcon} />
        <StatTile label="Wallets" value={stats.wallets_total} icon={WalletIcon} />
        <StatTile label="Transactions totales" value={stats.transactions_total} icon={ActivityIcon} />
        <StatTile
          label="Entrées d'audit système récentes"
          value={stats.system_logs_recent_count}
          icon={FileClockIcon}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Volume global déclaré (envois + paiements)</CardTitle>
        </CardHeader>
        <CardContent>
          {volumeEntries.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucune transaction enregistrée.</p>
          ) : (
            <div className="flex flex-wrap gap-4">
              {volumeEntries.map(([currency, amount]) => (
                <div key={currency} className="text-lg font-semibold tabular-nums">
                  {formatMoney(amount, currency)}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
