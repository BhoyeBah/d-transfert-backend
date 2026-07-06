"use client";

import { useTransition } from "react";
import { toast } from "sonner";

import { setAdminUserStatusAction } from "@/actions/admin";
import { Button } from "@/components/ui/button";

export function UserStatusActions({
  userId,
  companyId,
  isActive,
}: {
  userId: string;
  companyId: string | null;
  isActive: boolean;
}) {
  const [isPending, startTransition] = useTransition();

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      disabled={isPending}
      onClick={() =>
        startTransition(async () => {
          const result = await setAdminUserStatusAction(userId, companyId, !isActive);
          if (!result.ok) {
            toast.error(result.message);
            return;
          }
          toast.success(isActive ? "Compte suspendu." : "Compte réactivé.");
        })
      }
    >
      {isActive ? "Suspendre" : "Réactiver"}
    </Button>
  );
}
