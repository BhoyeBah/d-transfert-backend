import type { Metadata } from "next";
import Link from "next/link";

import { getCompanyMe } from "@/lib/data/company";
import { listWallets } from "@/lib/data/wallets";
import { formatMoney } from "@/lib/format";
import { walletTypeLabels } from "@/lib/validation/wallets";
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
import { CreateWalletDialog } from "./create-wallet-dialog";

export const metadata: Metadata = { title: "Wallets — D-Transfert" };

export default async function WalletsPage() {
  const [wallets, company] = await Promise.all([listWallets(), getCompanyMe()]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Wallets"
        description="Comptes de trésorerie de votre entreprise."
        action={<CreateWalletDialog defaultCurrency={company.default_currency} />}
      />

      {wallets.length === 0 ? (
        <EmptyState message="Aucun wallet créé pour le moment." />
      ) : (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nom</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Solde</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {wallets.map((wallet) => (
                <TableRow key={wallet.id}>
                  <TableCell className="font-medium">
                    <Link href={`/wallets/${wallet.id}`} className="hover:underline">
                      {wallet.name}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{wallet.code}</TableCell>
                  <TableCell>{walletTypeLabels[wallet.type]}</TableCell>
                  <TableCell>
                    <StatusBadge status={wallet.status} />
                  </TableCell>
                  <TableCell className="text-right font-medium tabular-nums">
                    {formatMoney(wallet.balance, wallet.currency)}
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
