"use client";

import { useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PlusIcon, Trash2Icon } from "lucide-react";
import { toast } from "sonner";

import { createEntryAction } from "@/actions/entries";
import { createEntrySchema, type EntryFormValues } from "@/lib/validation/entries";
import type { Wallet } from "@/types/api";
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

export function CreateEntryDialog({ wallets }: { wallets: Wallet[] }) {
  const [open, setOpen] = useState(false);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<EntryFormValues>({
    resolver: zodResolver(createEntrySchema),
    defaultValues: { lines: [{ wallet_id: "", amount: 0, currency: wallets[0]?.currency ?? "" }] },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "lines" });

  async function onSubmit(values: EntryFormValues) {
    const result = await createEntryAction(values);
    if (!result.ok) {
      toast.error(result.message);
      return;
    }
    toast.success(`Entrée ${result.data.reference} enregistrée.`);
    setOpen(false);
    reset();
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <PlusIcon />
          Nouvelle entrée
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Enregistrer une entrée</DialogTitle>
          <DialogDescription>Argent reçu d&apos;un client, à affecter ensuite à un envoi ou un paiement.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <Label>Lignes</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => append({ wallet_id: "", amount: 0, currency: wallets[0]?.currency ?? "" })}
              >
                <PlusIcon />
                Ajouter une ligne
              </Button>
            </div>
            {errors.lines?.root && <p className="text-sm text-destructive">{errors.lines.root.message}</p>}
            {fields.map((field, index) => (
              <div key={field.id} className="grid grid-cols-[1fr_auto_auto] items-end gap-2 rounded-md border border-border p-3">
                <div className="grid gap-1">
                  <Label className="text-xs">Wallet</Label>
                  <select
                    {...register(`lines.${index}.wallet_id`, {
                      onChange: (e) => {
                        const wallet = wallets.find((w) => w.id === e.target.value);
                        if (wallet) {
                          const currencyInput = document.querySelector<HTMLInputElement>(
                            `input[name="lines.${index}.currency"]`
                          );
                          if (currencyInput) currencyInput.value = wallet.currency;
                        }
                      },
                    })}
                    className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
                  >
                    <option value="">Choisir…</option>
                    {wallets.map((wallet) => (
                      <option key={wallet.id} value={wallet.id}>
                        {wallet.name} ({wallet.currency})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-1">
                  <Label className="text-xs">Montant</Label>
                  <Input type="number" min="0" step="0.01" className="w-28" {...register(`lines.${index}.amount`, { valueAsNumber: true })} />
                  <input type="hidden" {...register(`lines.${index}.currency`)} />
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  disabled={fields.length <= 1}
                  onClick={() => remove(index)}
                >
                  <Trash2Icon className="text-destructive" />
                </Button>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="client_name">Client (optionnel)</Label>
              <Input id="client_name" {...register("client_name")} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="client_phone">Téléphone client (optionnel)</Label>
              <Input id="client_phone" {...register("client_phone")} />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="note">Note (optionnel)</Label>
            <Input id="note" {...register("note")} />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Enregistrement..." : "Enregistrer"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
