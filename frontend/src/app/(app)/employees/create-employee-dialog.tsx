"use client";

import { useState } from "react";

import { createEmployeeAction } from "@/actions/employees";
import { CreateEntityDialog } from "@/components/create-entity-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PermissionCheckboxes } from "./permission-checkboxes";

export function CreateEmployeeDialog() {
  const [permissions, setPermissions] = useState<string[]>([]);

  return (
    <CreateEntityDialog
      triggerLabel="Nouvel employé"
      title="Créer un employé"
      description="Un matricule lui sera attribué automatiquement, à utiliser pour se connecter."
      action={createEmployeeAction}
      successMessage="Employé créé."
    >
      {(state) => (
        <>
          <div className="grid gap-1.5">
            <Label htmlFor="full_name">Nom complet</Label>
            <Input id="full_name" name="full_name" required />
            {state.fieldErrors?.full_name && (
              <p className="text-sm text-destructive">{state.fieldErrors.full_name[0]}</p>
            )}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="phone">Téléphone</Label>
            <Input id="phone" name="phone" required />
            {state.fieldErrors?.phone && (
              <p className="text-sm text-destructive">{state.fieldErrors.phone[0]}</p>
            )}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="password">Mot de passe</Label>
            <Input id="password" name="password" type="password" required />
            {state.fieldErrors?.password && (
              <p className="text-sm text-destructive">{state.fieldErrors.password[0]}</p>
            )}
          </div>
          <div className="grid gap-1.5">
            <Label>Permissions</Label>
            <PermissionCheckboxes name="permissions" selected={permissions} onChange={setPermissions} />
          </div>
        </>
      )}
    </CreateEntityDialog>
  );
}
