"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { cancelNationalOperationAction } from "@/actions/national-operations";
import { Button } from "@/components/ui/button";

export function CancelOperationButton({ operationId }: { operationId: string }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  return (
    <Button
      type="button"
      variant="outline"
      disabled={isPending}
      onClick={() =>
        startTransition(async () => {
          const result = await cancelNationalOperationAction(operationId);
          if (!result.ok) {
            toast.error(result.message);
            return;
          }
          toast.success("Opération annulée (mouvement inverse créé).");
          router.refresh();
        })
      }
    >
      Annuler l&apos;opération
    </Button>
  );
}
