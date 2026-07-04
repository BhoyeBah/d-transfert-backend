"use client";

import { useTransition } from "react";
import { CheckIcon } from "lucide-react";

import { markNotificationReadAction } from "@/actions/notifications";
import { Button } from "@/components/ui/button";

export function MarkNotificationReadButton({ notificationId }: { notificationId: string }) {
  const [isPending, startTransition] = useTransition();

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      disabled={isPending}
      onClick={() => startTransition(() => markNotificationReadAction(notificationId))}
    >
      <CheckIcon />
      Marquer comme lu
    </Button>
  );
}
