"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";

import { updateAdminSettingsAction } from "@/actions/admin";
import type { PlatformSettings } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

export function SettingsForm({ settings }: { settings: PlatformSettings }) {
  const [isPending, startTransition] = useTransition();
  const [maintenanceMode, setMaintenanceMode] = useState(settings.maintenance_mode);

  function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const currencies = String(formData.get("supported_currencies") ?? "")
      .split(",")
      .map((currency) => currency.trim().toUpperCase())
      .filter(Boolean);
    const maxAmountRaw = String(formData.get("max_transaction_amount") ?? "").trim();

    startTransition(async () => {
      const result = await updateAdminSettingsAction({
        supported_currencies: currencies,
        max_transaction_amount: maxAmountRaw ? Number(maxAmountRaw) : null,
        maintenance_mode: maintenanceMode,
      });
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Paramètres mis à jour.");
    });
  }

  return (
    <form onSubmit={onSubmit} className="flex max-w-md flex-col gap-4">
      <div className="grid gap-1.5">
        <Label htmlFor="supported_currencies">Devises supportées (séparées par des virgules)</Label>
        <Input
          id="supported_currencies"
          name="supported_currencies"
          defaultValue={settings.supported_currencies.join(", ")}
        />
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor="max_transaction_amount">Plafond de transaction (optionnel)</Label>
        <Input
          id="max_transaction_amount"
          name="max_transaction_amount"
          type="number"
          min="0"
          step="0.01"
          defaultValue={settings.max_transaction_amount ?? ""}
        />
      </div>
      <div className="flex items-center gap-2">
        <Switch
          id="maintenance_mode"
          checked={maintenanceMode}
          onCheckedChange={setMaintenanceMode}
        />
        <Label htmlFor="maintenance_mode">Mode maintenance</Label>
      </div>
      <div className="flex justify-end pt-2">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Enregistrement..." : "Enregistrer"}
        </Button>
      </div>
    </form>
  );
}
