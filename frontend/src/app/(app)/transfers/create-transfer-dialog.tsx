"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PlusIcon } from "lucide-react";
import { toast } from "sonner";

import { createTransferAction } from "@/actions/transfers";
import {
  SEND_MODES,
  createTransferSchema,
  sendModeLabels,
  type CreateTransferFormValues,
} from "@/lib/validation/transfers";
import type { Collaboration, Entry } from "@/types/api";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function CreateTransferDialog({
  collaborations,
  entries,
}: {
  collaborations: Collaboration[];
  entries: Entry[];
}) {
  const [open, setOpen] = useState(false);
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CreateTransferFormValues>({
    resolver: zodResolver(createTransferSchema),
    defaultValues: { send_mode: "cash" },
  });

  const collaborationId = watch("collaboration_id");
  const selectedCollaboration = collaborations.find((c) => c.id === collaborationId);
  const eligibleEntries = entries.filter(
    (entry) => !entry.merged_into_id && Object.keys(entry.available_by_currency).length > 0
  );

  async function onSubmit(values: CreateTransferFormValues) {
    const result = await createTransferAction(values);
    if (!result.ok) {
      toast.error(result.message);
      return;
    }
    toast.success(`Envoi ${result.data.reference} créé.`);
    setOpen(false);
    reset();
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <PlusIcon />
          Nouvel envoi
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Créer un envoi international</DialogTitle>
          <DialogDescription>
            Le taux collaboratif en vigueur sera figé sur cet envoi au moment de la création.
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
            <Label htmlFor="entry_id">Entrée à transformer (optionnel)</Label>
            <select
              id="entry_id"
              {...register("entry_id")}
              className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
            >
              <option value="">Aucune — solde direct</option>
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
                defaultValue={selectedCollaboration?.currency}
                {...register("currency")}
                onChange={(e) => setValue("currency", e.target.value.toUpperCase())}
              />
              {errors.currency && <p className="text-sm text-destructive">{errors.currency.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="beneficiary_name">Nom du bénéficiaire (optionnel)</Label>
              <Input id="beneficiary_name" {...register("beneficiary_name")} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="beneficiary_phone">Téléphone du bénéficiaire</Label>
              <Input id="beneficiary_phone" {...register("beneficiary_phone")} required />
              {errors.beneficiary_phone && (
                <p className="text-sm text-destructive">{errors.beneficiary_phone.message}</p>
              )}
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label htmlFor="send_mode">Mode d&apos;envoi</Label>
            <Select defaultValue="cash" onValueChange={(v) => setValue("send_mode", v as typeof SEND_MODES[number])}>
              <SelectTrigger id="send_mode" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SEND_MODES.map((mode) => (
                  <SelectItem key={mode} value={mode}>
                    {sendModeLabels[mode]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="client_name">Client (si le montant dépasse l&apos;entrée)</Label>
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
              {isSubmitting ? "Création..." : "Créer l'envoi"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
