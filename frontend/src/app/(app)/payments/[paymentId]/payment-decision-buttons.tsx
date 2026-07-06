"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { approvePaymentAction, rejectPaymentAction } from "@/actions/payments";
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

export function PaymentDecisionButtons({ paymentId }: { paymentId: string }) {
  const [isPending, startTransition] = useTransition();
  const [rejectOpen, setRejectOpen] = useState(false);
  const router = useRouter();

  function approve() {
    startTransition(async () => {
      const result = await approvePaymentAction(paymentId);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Paiement approuvé.");
      router.refresh();
    });
  }

  function reject(formData: FormData) {
    const reason = String(formData.get("reason") ?? "");
    startTransition(async () => {
      const result = await rejectPaymentAction(paymentId, reason);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Paiement rejeté.");
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
            <DialogTitle>Rejeter le paiement</DialogTitle>
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
