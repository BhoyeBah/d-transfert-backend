"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { setEmployeeStatusAction, updateEmployeePermissionsAction } from "@/actions/employees";
import type { Employee } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { PermissionCheckboxes } from "./permission-checkboxes";

export function EmployeeRowActions({ employee }: { employee: Employee }) {
  const [open, setOpen] = useState(false);
  const [permissions, setPermissions] = useState<string[]>(employee.permissions);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function savePermissions() {
    startTransition(async () => {
      const result = await updateEmployeePermissionsAction(employee.id, employee.permissions, permissions);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Permissions mises à jour.");
      setOpen(false);
      router.refresh();
    });
  }

  function toggleStatus(next: boolean) {
    startTransition(async () => {
      const result = await setEmployeeStatusAction(employee.id, next);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success(next ? "Employé réactivé." : "Employé désactivé.");
      router.refresh();
    });
  }

  return (
    <div className="flex items-center justify-end gap-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Switch checked={employee.is_active} onCheckedChange={toggleStatus} disabled={isPending} />
        {employee.is_active ? "Actif" : "Désactivé"}
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            Permissions
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Permissions de {employee.full_name}</DialogTitle>
          </DialogHeader>
          <PermissionCheckboxes name="permissions" selected={permissions} onChange={setPermissions} />
          <DialogFooter>
            <Button onClick={savePermissions} disabled={isPending}>
              {isPending ? "Enregistrement..." : "Enregistrer"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
