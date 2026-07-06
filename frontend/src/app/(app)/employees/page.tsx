import type { Metadata } from "next";

import { listEmployees } from "@/lib/data/employees";
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
import { CreateEmployeeDialog } from "./create-employee-dialog";
import { EmployeeRowActions } from "./employee-row-actions";

export const metadata: Metadata = { title: "Employés — D-Transfert" };

export default async function EmployeesPage() {
  const employees = await listEmployees();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Employés"
        description="Comptes employés et leurs permissions."
        action={<CreateEmployeeDialog />}
      />

      {employees.length === 0 ? (
        <EmptyState message="Aucun employé créé." />
      ) : (
        <Card className="py-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nom</TableHead>
                <TableHead>Matricule</TableHead>
                <TableHead>Téléphone</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {employees.map((employee) => (
                <TableRow key={employee.id}>
                  <TableCell className="font-medium">{employee.full_name}</TableCell>
                  <TableCell className="font-mono text-xs">{employee.matricule}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{employee.phone}</TableCell>
                  <TableCell>
                    <StatusBadge status={employee.is_active ? "active" : "inactive"} />
                  </TableCell>
                  <TableCell>
                    <EmployeeRowActions employee={employee} />
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
