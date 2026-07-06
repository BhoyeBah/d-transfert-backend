"use client";

import { useState } from "react";

import { createSupplierAction } from "@/actions/suppliers";
import { CreateEntityDialog } from "@/components/create-entity-dialog";
import { CurrencySelect } from "@/components/currency-select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function CreateSupplierDialog({ defaultCurrency }: { defaultCurrency: string }) {
  const [currency, setCurrency] = useState(defaultCurrency);

  return (
    <CreateEntityDialog
      triggerLabel="Nouveau fournisseur"
      title="Ajouter un fournisseur"
      action={createSupplierAction}
      successMessage="Fournisseur ajouté."
    >
      {(state) => (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="name">Nom</Label>
              <Input id="name" name="name" required />
              {state.fieldErrors?.name && (
                <p className="text-sm text-destructive">{state.fieldErrors.name[0]}</p>
              )}
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="code">Code</Label>
              <Input id="code" name="code" required />
              {state.fieldErrors?.code && (
                <p className="text-sm text-destructive">{state.fieldErrors.code[0]}</p>
              )}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="currency">Devise</Label>
              <CurrencySelect id="currency" name="currency" value={currency} onValueChange={setCurrency} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="initial_balance">Solde initial</Label>
              <Input id="initial_balance" name="initial_balance" type="number" step="0.01" defaultValue="0" />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="phone">Téléphone (optionnel)</Label>
            <Input id="phone" name="phone" />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="address">Adresse (optionnel)</Label>
            <Input id="address" name="address" />
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
