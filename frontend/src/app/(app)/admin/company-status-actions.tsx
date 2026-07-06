"use client";

import { useTransition } from "react";
import { toast } from "sonner";

import { setAdminCompanyStatusAction } from "@/actions/admin";
import { Button } from "@/components/ui/button";
import type { CompanyStatus } from "@/types/api";

const STATUS_ACTIONS: { status: CompanyStatus; label: string }[] = [
  { status: "active", label: "Activer" },
  { status: "pending", label: "Mettre en attente" },
  { status: "suspended", label: "Suspendre" },
];

export function CompanyStatusActions({ companyId, status }: { companyId: string; status: CompanyStatus }) {
  const [isPending, startTransition] = useTransition();

  return (
    <div className="flex flex-wrap gap-2">
      {STATUS_ACTIONS.filter((action) => action.status !== status).map((action) => (
        <Button
          key={action.status}
          type="button"
          variant="outline"
          size="sm"
          disabled={isPending}
          onClick={() =>
            startTransition(async () => {
              const result = await setAdminCompanyStatusAction(companyId, action.status);
              if (!result.ok) {
                toast.error(result.message);
                return;
              }
              toast.success("Statut de l'entreprise mis à jour.");
            })
          }
        >
          {action.label}
        </Button>
      ))}
    </div>
  );
}
