"use client";

import { useState } from "react";

import { createPrivateRateAction } from "@/actions/collaborations";
import { CreateEntityDialog } from "@/components/create-entity-dialog";
import { CurrencySelect } from "@/components/currency-select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function CreatePrivateRateDialog({
  collaborationId,
  defaultCurrency,
}: {
  collaborationId: string;
  defaultCurrency: string;
}) {
  const [currency, setCurrency] = useState(defaultCurrency);

  return (
    <CreateEntityDialog
      triggerLabel="Définir un taux privé"
      title="Taux d'envoi privé"
      description="Visible uniquement par votre entreprise — jamais par le collaborateur."
      action={createPrivateRateAction}
      successMessage="Taux privé enregistré."
    >
      {(state) => (
        <>
          <input type="hidden" name="collaboration_id" value={collaborationId} />
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="currency">Devise</Label>
              <CurrencySelect id="currency" name="currency" value={currency} onValueChange={setCurrency} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="rate">Taux</Label>
              <Input id="rate" name="rate" type="number" min="0" step="0.000001" required />
              {state.fieldErrors?.rate && (
                <p className="text-sm text-destructive">{state.fieldErrors.rate[0]}</p>
              )}
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="country">Pays (optionnel)</Label>
            <Input id="country" name="country" />
          </div>
        </>
      )}
    </CreateEntityDialog>
  );
}
