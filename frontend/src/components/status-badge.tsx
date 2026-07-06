import { Badge, type badgeVariants } from "@/components/ui/badge";
import type { VariantProps } from "class-variance-authority";

type Variant = VariantProps<typeof badgeVariants>["variant"];

const STATUS_CONFIG: Record<string, { label: string; variant: Variant }> = {
  // wallets
  active: { label: "Actif", variant: "success" },
  inactive: { label: "Inactif", variant: "secondary" },
  // national operations / entries shared
  draft: { label: "Brouillon", variant: "secondary" },
  validated: { label: "Validée", variant: "success" },
  cancelled: { label: "Annulée", variant: "secondary" },
  corrected: { label: "Corrigée", variant: "secondary" },
  unallocated: { label: "Disponible", variant: "outline" },
  partially_allocated: { label: "Partiellement affectée", variant: "warning" },
  allocated: { label: "Affectée", variant: "secondary" },
  consumed: { label: "Consommée", variant: "secondary" },
  rejected: { label: "Rejetée", variant: "destructive" },
  // transfers / payments
  pending: { label: "En attente", variant: "warning" },
  approved: { label: "Approuvé", variant: "success" },
  // collaborations
  accepted: { label: "Acceptée", variant: "success" },
  suspended: { label: "Suspendue", variant: "secondary" },
  archived: { label: "Archivée", variant: "secondary" },
  proposed: { label: "Proposé", variant: "warning" },
  // system logs / subscriptions
  info: { label: "Info", variant: "outline" },
  warning: { label: "Avertissement", variant: "warning" },
  error: { label: "Erreur", variant: "destructive" },
  expired: { label: "Expiré", variant: "secondary" },
  free: { label: "Gratuit", variant: "outline" },
  standard: { label: "Standard", variant: "secondary" },
  premium: { label: "Premium", variant: "success" },
};

export function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] ?? { label: status, variant: "outline" as Variant };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
