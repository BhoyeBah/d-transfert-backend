"use client";

import { useTransition } from "react";
import { toast } from "sonner";

import { setWalletStatusAction } from "@/actions/wallets";
import { Button } from "@/components/ui/button";
import type { WalletStatus } from "@/types/api";

export function ToggleWalletStatusButton({ walletId, status }: { walletId: string; status: WalletStatus }) {
  const [isPending, startTransition] = useTransition();
  const next = status === "active" ? "inactive" : "active";

  return (
    <Button
      type="button"
      variant="outline"
      disabled={isPending}
      onClick={() =>
        startTransition(async () => {
          await setWalletStatusAction(walletId, next);
          toast.success(next === "active" ? "Wallet réactivé." : "Wallet désactivé.");
        })
      }
    >
      {status === "active" ? "Désactiver" : "Réactiver"}
    </Button>
  );
}
