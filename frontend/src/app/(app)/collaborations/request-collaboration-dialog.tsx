"use client";

import { useState } from "react";

import { requestCollaborationAction } from "@/actions/collaborations";
import { CreateEntityDialog } from "@/components/create-entity-dialog";
import { CurrencySelect } from "@/components/currency-select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function RequestCollaborationDialog({ defaultCurrency }: { defaultCurrency: string }) {
  const [currency, setCurrency] = useState(defaultCurrency);

  return (
    <CreateEntityDialog
      triggerLabel="Demander une collaboration"
      title="Demander une collaboration"
      description="Recherchez l'entreprise partenaire par son matricule."
      action={requestCollaborationAction}
      successMessage="Demande de collaboration envoyée."
    >
      {(state) => (
        <>
          <div className="grid gap-1.5">
            <Label htmlFor="target_matricule">Matricule de l&apos;entreprise partenaire</Label>
            <Input id="target_matricule" name="target_matricule" placeholder="DT-XXXXXXXX" required />
            {state.fieldErrors?.target_matricule && (
              <p className="text-sm text-destructive">{state.fieldErrors.target_matricule[0]}</p>
            )}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="currency">Devise de la collaboration</Label>
              <CurrencySelect id="currency" name="currency" value={currency} onValueChange={setCurrency} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="initial_rate">Taux collaboratif initial</Label>
              <Input id="initial_rate" name="initial_rate" type="number" min="0" step="0.000001" required />
              {state.fieldErrors?.initial_rate && (
                <p className="text-sm text-destructive">{state.fieldErrors.initial_rate[0]}</p>
              )}
            </div>
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
