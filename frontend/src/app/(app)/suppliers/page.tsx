import type { Metadata } from "next";
import Link from "next/link";

import { listSuppliers } from "@/lib/data/suppliers";
import { formatMoney } from "@/lib/format";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CreateSupplierDialog } from "./create-supplier-dialog";
import { getCompanyMe } from "@/lib/data/company";

export const metadata: Metadata = { title: "Fournisseurs — D-Transfert" };

export default async function SuppliersPage() {
  const [suppliers, company] = await Promise.all([listSuppliers(), getCompanyMe()]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Fournisseurs"
        description="Fournisseurs et suivi de leurs dettes/paiements."
        action={<CreateSupplierDialog defaultCurrency={company.default_currency} />}
      />

      {suppliers.length === 0 ? (
        <EmptyState message="Aucun fournisseur enregistré." />
      ) : (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nom</TableHead>
                <TableHead>Code</TableHead>
                <TableHead className="text-right">Solde</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {suppliers.map((supplier) => (
                <TableRow key={supplier.id}>
                  <TableCell className="font-medium">
                    <Link href={`/suppliers/${supplier.id}`} className="hover:underline">
                      {supplier.name}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{supplier.code}</TableCell>
                  <TableCell className="text-right font-medium tabular-nums">
                    {formatMoney(supplier.balance, supplier.currency)}
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
