"use client";

import { useTransition } from "react";
import { toast } from "sonner";

import { updateAdminSubscriptionAction } from "@/actions/admin";
import type { Subscription, SubscriptionPlan, SubscriptionStatus } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const PLAN_LABELS: Record<SubscriptionPlan, string> = {
  free: "Gratuit",
  standard: "Standard",
  premium: "Premium",
};

const STATUS_LABELS: Record<SubscriptionStatus, string> = {
  active: "Active",
  expired: "Expirée",
  cancelled: "Annulée",
};

export function SubscriptionForm({
  companyId,
  subscription,
}: {
  companyId: string;
  subscription: Subscription;
}) {
  const [isPending, startTransition] = useTransition();

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const priceRaw = String(formData.get("price") ?? "").trim();

    startTransition(async () => {
      const result = await updateAdminSubscriptionAction(companyId, {
        plan: formData.get("plan") as SubscriptionPlan,
        status: formData.get("status") as SubscriptionStatus,
        price: priceRaw ? Number(priceRaw) : null,
        currency: String(formData.get("currency") ?? "").trim() || null,
      });
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Abonnement mis à jour.");
    });
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="grid gap-1.5">
          <Label htmlFor="plan">Plan</Label>
          <select
            id="plan"
            name="plan"
            defaultValue={subscription.plan}
            className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
          >
            {Object.entries(PLAN_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="status">Statut</Label>
          <select
            id="status"
            name="status"
            defaultValue={subscription.status}
            className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
          >
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="grid gap-1.5">
          <Label htmlFor="price">Prix (optionnel)</Label>
          <Input id="price" name="price" type="number" min="0" step="0.01" defaultValue={subscription.price ?? ""} />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="currency">Devise</Label>
          <Input id="currency" name="currency" defaultValue={subscription.currency ?? ""} />
        </div>
      </div>
      <div className="flex justify-end pt-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Enregistrement..." : "Enregistrer l'abonnement"}
        </Button>
      </div>
    </form>
  );
}
