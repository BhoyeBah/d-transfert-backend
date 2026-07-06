"use client";

import { createClientAction } from "@/actions/clients";
import { CreateEntityDialog } from "@/components/create-entity-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function CreateClientDialog() {
  return (
    <CreateEntityDialog
      triggerLabel="Nouveau client"
      title="Ajouter un client"
      action={createClientAction}
      successMessage="Client ajouté."
    >
      {(state) => (
        <>
          <div className="grid gap-1.5">
            <Label htmlFor="name">Nom</Label>
            <Input id="name" name="name" required />
            {state.fieldErrors?.name && <p className="text-sm text-destructive">{state.fieldErrors.name[0]}</p>}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="phone">Téléphone</Label>
            <Input id="phone" name="phone" required />
            {state.fieldErrors?.phone && (
              <p className="text-sm text-destructive">{state.fieldErrors.phone[0]}</p>
            )}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="note">Note (optionnel)</Label>
            <Input id="note" name="note" />
          </div>
        </>
      )}
    </CreateEntityDialog>
  );
}
