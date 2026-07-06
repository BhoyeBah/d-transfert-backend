"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { approveTransferAction, rejectTransferAction } from "@/actions/transfers";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function TransferDecisionButtons({ transferId }: { transferId: string }) {
  const [isPending, startTransition] = useTransition();
  const [rejectOpen, setRejectOpen] = useState(false);
  const router = useRouter();

  function approve() {
    startTransition(async () => {
      const result = await approveTransferAction(transferId);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Envoi approuvé.");
      router.refresh();
    });
  }

  function reject(formData: FormData) {
    const reason = String(formData.get("reason") ?? "");
    startTransition(async () => {
      const result = await rejectTransferAction(transferId, reason);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Envoi rejeté.");
      setRejectOpen(false);
      router.refresh();
    });
  }

  return (
    <div className="flex gap-2">
      <Button size="sm" disabled={isPending} onClick={approve}>
        Approuver
      </Button>
      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogTrigger asChild>
          <Button size="sm" variant="outline" disabled={isPending}>
            Rejeter
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rejeter l&apos;envoi</DialogTitle>
          </DialogHeader>
          <form action={reject} className="flex flex-col gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="reason">Motif du rejet</Label>
              <Textarea id="reason" name="reason" required />
            </div>
            <DialogFooter>
              <Button type="submit" variant="destructive" disabled={isPending}>
                Confirmer le rejet
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
