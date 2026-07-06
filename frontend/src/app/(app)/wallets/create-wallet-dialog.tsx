"use client";

import { useState } from "react";

import { createWalletAction } from "@/actions/wallets";
import { WALLET_TYPES, walletTypeLabels } from "@/lib/validation/wallets";
import { CreateEntityDialog } from "@/components/create-entity-dialog";
import { CurrencySelect } from "@/components/currency-select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function CreateWalletDialog({ defaultCurrency }: { defaultCurrency: string }) {
  const [currency, setCurrency] = useState(defaultCurrency);
  const [type, setType] = useState<(typeof WALLET_TYPES)[number]>("cash");

  return (
    <CreateEntityDialog
      triggerLabel="Nouveau wallet"
      title="Créer un wallet"
      description="Un compte de trésorerie (caisse, mobile money, banque...) pour votre entreprise."
      action={createWalletAction}
      successMessage="Wallet créé."
    >
      {(state) => (
        <>
          <div className="grid gap-1.5">
            <Label htmlFor="name">Nom</Label>
            <Input id="name" name="name" required />
            {state.fieldErrors?.name && <p className="text-sm text-destructive">{state.fieldErrors.name[0]}</p>}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="code">Code</Label>
              <Input id="code" name="code" placeholder="CASH-01" required />
              {state.fieldErrors?.code && (
                <p className="text-sm text-destructive">{state.fieldErrors.code[0]}</p>
              )}
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="type">Type</Label>
              <Select value={type} onValueChange={(v) => setType(v as typeof type)}>
                <SelectTrigger id="type" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {WALLET_TYPES.map((value) => (
                    <SelectItem key={value} value={value}>
                      {walletTypeLabels[value]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <input type="hidden" name="type" value={type} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="currency">Devise</Label>
              <CurrencySelect id="currency" name="currency" value={currency} onValueChange={setCurrency} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="initial_balance">Solde initial</Label>
              <Input id="initial_balance" name="initial_balance" type="number" min="0" step="0.01" defaultValue="0" />
              {state.fieldErrors?.initial_balance && (
                <p className="text-sm text-destructive">{state.fieldErrors.initial_balance[0]}</p>
              )}
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="phone">Téléphone (optionnel)</Label>
            <Input id="phone" name="phone" />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="description">Description (optionnel)</Label>
            <Input id="description" name="description" />
          </div>
        </>
      )}
    </CreateEntityDialog>
  );
}
