"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { rebalanceSupplierAction } from "@/actions/suppliers";
import {
  SUPPLIER_MOVEMENT_TYPES,
  rebalanceSupplierSchema,
  supplierMovementTypeLabels,
  type RebalanceSupplierFormValues,
} from "@/lib/validation/suppliers";
import type { Wallet } from "@/types/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
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

export function RebalanceSupplierDialog({ supplierId, wallets }: { supplierId: string; wallets: Wallet[] }) {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<(typeof SUPPLIER_MOVEMENT_TYPES)[number]>("payment");
  const router = useRouter();
  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RebalanceSupplierFormValues>({
    resolver: zodResolver(rebalanceSupplierSchema),
    defaultValues: { type: "payment" },
  });

  async function onSubmit(values: RebalanceSupplierFormValues) {
    const result = await rebalanceSupplierAction(supplierId, values);
    if (!result.ok) {
      toast.error(result.message);
      return;
    }
    toast.success("Mouvement enregistré.");
    setOpen(false);
    reset();
    router.refresh();
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">Nouveau mouvement</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Dette ou paiement fournisseur</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="type">Type</Label>
            <Select
              value={type}
              onValueChange={(v) => {
                setType(v as typeof type);
                setValue("type", v as typeof type);
              }}
            >
              <SelectTrigger id="type" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SUPPLIER_MOVEMENT_TYPES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {supplierMovementTypeLabels[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
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
                  {wallet.name} ({wallet.currency})
                </option>
              ))}
            </select>
            {errors.wallet_id && <p className="text-sm text-destructive">{errors.wallet_id.message}</p>}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="amount">Montant</Label>
            <Input id="amount" type="number" min="0" step="0.01" {...register("amount", { valueAsNumber: true })} />
            {errors.amount && <p className="text-sm text-destructive">{errors.amount.message}</p>}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="note">Note (optionnel)</Label>
            <Input id="note" {...register("note")} />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Enregistrement..." : "Enregistrer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
