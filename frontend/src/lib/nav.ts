import { PermissionCode } from "@/lib/permissions";

export type NavIconName =
  | "dashboard"
  | "wallet"
  | "landmark"
  | "scroll-text"
  | "arrow-left-right"
  | "hand-coins"
  | "building"
  | "users"
  | "truck"
  | "file-clock"
  | "shield-check"
  | "shield-alert";

export type NavItem = {
  href: string;
  label: string;
  icon: NavIconName;
  /** null = visible to any authenticated user (dashboard, notifications). */
  requiredPermission: PermissionCode | null;
};

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Tableau de bord", icon: "dashboard", requiredPermission: null },
  { href: "/wallets", label: "Wallets", icon: "wallet", requiredPermission: PermissionCode.WALLET_MANAGE },
  {
    href: "/national-operations",
    label: "Opérations nationales",
    icon: "landmark",
    requiredPermission: PermissionCode.NATIONAL_OPERATION_MANAGE,
  },
  {
    href: "/entries",
    label: "Entrées",
    icon: "scroll-text",
    requiredPermission: PermissionCode.ENTRY_MANAGE,
  },
  {
    href: "/transfers",
    label: "Envois internationaux",
    icon: "arrow-left-right",
    requiredPermission: PermissionCode.TRANSFER_CREATE,
  },
  {
    href: "/payments",
    label: "Paiements collaborateurs",
    icon: "hand-coins",
    requiredPermission: PermissionCode.PAYMENT_CREATE,
  },
  {
    href: "/collaborations",
    label: "Collaborations",
    icon: "building",
    requiredPermission: PermissionCode.COLLABORATION_MANAGE,
  },
  { href: "/clients", label: "Clients", icon: "users", requiredPermission: PermissionCode.CLIENT_MANAGE },
  {
    href: "/suppliers",
    label: "Fournisseurs",
    icon: "truck",
    requiredPermission: PermissionCode.SUPPLIER_MANAGE,
  },
  {
    href: "/reports",
    label: "Rapports",
    icon: "file-clock",
    requiredPermission: PermissionCode.REPORT_VIEW,
  },
  {
    href: "/employees",
    label: "Employés",
    icon: "shield-check",
    requiredPermission: PermissionCode.EMPLOYEE_MANAGE,
  },
];

/**
 * The Super Admin platform role has no company_id, so every company-scoped
 * endpoint (dashboard, wallets, entries, ...) rejects it. It only ever sees
 * this single platform-wide section.
 */
export const SUPER_ADMIN_NAV_ITEMS: NavItem[] = [
  {
    href: "/admin",
    label: "Administration plateforme",
    icon: "shield-alert",
    requiredPermission: null,
  },
];
