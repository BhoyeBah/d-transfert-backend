"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PlusIcon } from "lucide-react";
import { toast } from "sonner";

import { createPaymentAction } from "@/actions/payments";
import { createPaymentSchema, type CreatePaymentFormValues } from "@/lib/validation/payments";
import type { Collaboration, Entry, Wallet } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Source = "none" | "entry" | "wallet";

export function CreatePaymentDialog({
  collaborations,
  entries,
  wallets,
}: {
  collaborations: Collaboration[];
  entries: Entry[];
  wallets: Wallet[];
}) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<Source>("none");
  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreatePaymentFormValues>({ resolver: zodResolver(createPaymentSchema) });

  const eligibleEntries = entries.filter(
    (entry) => !entry.merged_into_id && Object.keys(entry.available_by_currency).length > 0
  );

  function changeSource(next: Source) {
    setSource(next);
    setValue("entry_id", next === "entry" ? "" : undefined);
    setValue("wallet_id", next === "wallet" ? "" : undefined);
  }

  async function onSubmit(values: CreatePaymentFormValues) {
    const result = await createPaymentAction(values);
    if (!result.ok) {
      toast.error(result.message);
      return;
    }
    toast.success(`Paiement ${result.data.reference} créé.`);
    setOpen(false);
    reset();
    setSource("none");
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <PlusIcon />
          Nouveau paiement
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Créer un paiement collaborateur</DialogTitle>
          <DialogDescription>
            Règle une dette existante (via une entrée) ou constitue un paiement direct depuis un wallet.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="collaboration_id">Collaboration</Label>
            <select
              id="collaboration_id"
              {...register("collaboration_id")}
              className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
            >
              <option value="">Choisir…</option>
              {collaborations.map((collaboration) => (
                <option key={collaboration.id} value={collaboration.id}>
                  {collaboration.currency} · taux {collaboration.current_rate}
                </option>
              ))}
            </select>
            {errors.collaboration_id && (
              <p className="text-sm text-destructive">{errors.collaboration_id.message}</p>
            )}
          </div>

          <div className="grid gap-1.5">
            <Label>Source des fonds</Label>
            <div className="flex gap-2">
              {(["none", "entry", "wallet"] as const).map((value) => (
                <Button
                  key={value}
                  type="button"
                  size="sm"
                  variant={source === value ? "default" : "outline"}
                  onClick={() => changeSource(value)}
                >
                  {value === "none" ? "Aucune" : value === "entry" ? "Depuis une entrée" : "Depuis un wallet"}
                </Button>
              ))}
            </div>
          </div>

          {source === "entry" && (
            <div className="grid gap-1.5">
              <Label htmlFor="entry_id">Entrée</Label>
              <select
                id="entry_id"
                {...register("entry_id")}
                className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
              >
                <option value="">Choisir…</option>
                {eligibleEntries.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.reference} —{" "}
                    {Object.entries(entry.available_by_currency)
                      .map(([currency, amount]) => `${amount} ${currency}`)
                      .join(", ")}
                  </option>
                ))}
              </select>
            </div>
          )}

          {source === "wallet" && (
            <div className="grid gap-1.5">
              <Label htmlFor="wallet_id">Wallet</Label>
              <select
                id="wallet_id"
                {...register("wallet_id")}
                className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
              >
                <option value="">Choisir…</option>
                {wallets.map((wallet) => (
                  <option key={wallet.id} value={wallet.id}>
                    {wallet.name} ({wallet.currency}) — {wallet.balance}
                  </option>
                ))}
              </select>
              {errors.wallet_id && <p className="text-sm text-destructive">{errors.wallet_id.message}</p>}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="amount">Montant</Label>
              <Input id="amount" type="number" min="0" step="0.01" {...register("amount", { valueAsNumber: true })} />
              {errors.amount && <p className="text-sm text-destructive">{errors.amount.message}</p>}
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="currency">Devise</Label>
              <Input
                id="currency"
                {...register("currency")}
                onChange={(e) => setValue("currency", e.target.value.toUpperCase())}
              />
              {errors.currency && <p className="text-sm text-destructive">{errors.currency.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="client_name">Client (si dépassement)</Label>
              <Input id="client_name" {...register("client_name")} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="client_phone">Téléphone client</Label>
              <Input id="client_phone" {...register("client_phone")} />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="note">Note (optionnel)</Label>
            <Input id="note" {...register("note")} />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Création..." : "Créer le paiement"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
