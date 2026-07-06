"use client";

import { createPlatformAdminAction } from "@/actions/admin";
import { CreateEntityDialog } from "@/components/create-entity-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function CreatePlatformAdminDialog() {
  return (
    <CreateEntityDialog
      triggerLabel="Nouveau Super Admin"
      title="Créer un compte Super Admin"
      description="Ce compte aura un accès total à l'administration de la plateforme, sur toutes les entreprises."
      action={createPlatformAdminAction}
      successMessage="Compte Super Admin créé."
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
        </>
      )}
    </CreateEntityDialog>
  );
}
