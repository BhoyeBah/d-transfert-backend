"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import {
  acceptCollaborationAction,
  decideRateProposalAction,
  proposeRateAction,
  rejectCollaborationAction,
} from "@/actions/collaborations";
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

export function CollaborationDecisionButtons({ collaborationId }: { collaborationId: string }) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function accept() {
    startTransition(async () => {
      const result = await acceptCollaborationAction(collaborationId);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Collaboration acceptée.");
      router.refresh();
    });
  }

  function reject() {
    startTransition(async () => {
      const result = await rejectCollaborationAction(collaborationId);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Collaboration rejetée.");
      router.refresh();
    });
  }

  return (
    <div className="flex gap-2">
      <Button size="sm" disabled={isPending} onClick={accept}>
        Accepter
      </Button>
      <Button size="sm" variant="outline" disabled={isPending} onClick={reject}>
        Rejeter
      </Button>
    </div>
  );
}

export function ProposeRateDialog({ collaborationId }: { collaborationId: string }) {
  const [open, setOpen] = useState(false);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function submit(formData: FormData) {
    const newRate = Number(formData.get("new_rate"));
    const note = String(formData.get("note") ?? "");
    startTransition(async () => {
      const result = await proposeRateAction(collaborationId, { new_rate: newRate, note });
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success("Nouveau taux proposé.");
      setOpen(false);
      router.refresh();
    });
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          Proposer un nouveau taux
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Proposer un nouveau taux collaboratif</DialogTitle>
        </DialogHeader>
        <form action={submit} className="flex flex-col gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="new_rate">Nouveau taux</Label>
            <Input id="new_rate" name="new_rate" type="number" min="0" step="0.000001" required />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="note">Note (optionnel)</Label>
            <Input id="note" name="note" />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={isPending}>
              {isPending ? "Envoi..." : "Proposer"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function RateProposalDecisionButtons({
  collaborationId,
  proposalId,
}: {
  collaborationId: string;
  proposalId: string;
}) {
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function decide(decision: "accept" | "reject") {
    startTransition(async () => {
      const result = await decideRateProposalAction(collaborationId, proposalId, decision);
      if (!result.ok) {
        toast.error(result.message);
        return;
      }
      toast.success(decision === "accept" ? "Taux accepté." : "Proposition rejetée.");
      router.refresh();
    });
  }

  return (
    <div className="flex gap-2">
      <Button size="sm" disabled={isPending} onClick={() => decide("accept")}>
        Accepter
      </Button>
      <Button size="sm" variant="outline" disabled={isPending} onClick={() => decide("reject")}>
        Rejeter
      </Button>
    </div>
  );
}
