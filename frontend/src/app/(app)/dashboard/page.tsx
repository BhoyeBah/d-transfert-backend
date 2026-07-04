import type { Metadata } from "next";
import {
  ArrowLeftRight,
  Building2,
  Clock,
  HandCoins,
  ScrollText,
  Truck,
  Users,
  Wallet,
  XCircle,
} from "lucide-react";

import { getDashboard } from "@/lib/data/dashboard";
import { formatMoney } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatTile } from "@/components/stat-tile";

export const metadata: Metadata = { title: "Tableau de bord — D-Transfert" };

export default async function DashboardPage() {
  const dashboard = await getDashboard();
  const walletCurrencies = Object.entries(dashboard.wallets_balance_by_currency);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">Tableau de bord</h1>
        <p className="text-sm text-muted-foreground">Vue d&apos;ensemble de votre activité du jour.</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {walletCurrencies.length > 0 ? (
          walletCurrencies.map(([currency, balance]) => (
            <StatTile
              key={currency}
              label={`Solde wallets ${currency}`}
              value={formatMoney(balance, currency)}
              icon={Wallet}
            />
          ))
        ) : (
          <StatTile label="Solde wallets" value="—" icon={Wallet} hint="Aucun wallet créé" />
        )}
        <StatTile label="Entrées aujourd'hui" value={dashboard.entries_today_count} icon={ScrollText} />
        <StatTile
          label="Opérations nationales"
          value={dashboard.national_operations_today_count}
          icon={Building2}
          hint="aujourd'hui"
        />
        <StatTile
          label="Collaborations actives"
          value={dashboard.active_collaborations_count}
          icon={Users}
        />
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Envois aujourd'hui"
          value={dashboard.transfers_today_count}
          icon={ArrowLeftRight}
        />
        <StatTile
          label="Envois en attente"
          value={dashboard.transfers_pending_count}
          icon={Clock}
          tone={dashboard.transfers_pending_count > 0 ? "warning" : "default"}
        />
        <StatTile
          label="Paiements en attente"
          value={dashboard.payments_pending_count}
          icon={Clock}
          tone={dashboard.payments_pending_count > 0 ? "warning" : "default"}
        />
        <StatTile
          label="Opérations rejetées"
          value={dashboard.transfers_rejected_count + dashboard.payments_rejected_count}
          icon={XCircle}
          tone={
            dashboard.transfers_rejected_count + dashboard.payments_rejected_count > 0
              ? "destructive"
              : "default"
          }
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Solde par collaborateur</CardTitle>
          </CardHeader>
          <CardContent>
            {dashboard.collaborator_balances.length === 0 ? (
              <p className="text-sm text-muted-foreground">Aucune collaboration active.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Collaboration</TableHead>
                    <TableHead>Devise</TableHead>
                    <TableHead className="text-right">Solde</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dashboard.collaborator_balances.map((balance) => (
                    <TableRow key={balance.collaboration_id}>
                      <TableCell className="font-mono text-xs">
                        {balance.collaboration_id.slice(0, 8)}
                      </TableCell>
                      <TableCell>{balance.currency}</TableCell>
                      <TableCell
                        className={`text-right font-medium tabular-nums ${
                          Number(balance.balance) < 0 ? "text-destructive" : "text-success"
                        }`}
                      >
                        {formatMoney(balance.balance, balance.currency)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <StatTile
            label="Dettes clients"
            value={formatMoney(dashboard.clients_total_balance)}
            icon={HandCoins}
          />
          <StatTile
            label="Dettes fournisseurs"
            value={formatMoney(dashboard.suppliers_total_balance)}
            icon={Truck}
          />
        </div>
      </section>
    </div>
  );
}
