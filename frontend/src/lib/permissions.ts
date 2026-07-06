export const PermissionCode = {
  DASHBOARD_VIEW: "dashboard.view",
  ENTRY_MANAGE: "entry.manage",
  TRANSFER_CREATE: "transfer.create",
  PAYMENT_CREATE: "payment.create",
  OPERATION_VALIDATE: "operation.validate",
  WALLET_MANAGE: "wallet.manage",
  NATIONAL_OPERATION_MANAGE: "national_operation.manage",
  COLLABORATION_MANAGE: "collaboration.manage",
  SUPPLIER_MANAGE: "supplier.manage",
  CLIENT_MANAGE: "client.manage",
  REPORT_VIEW: "report.view",
  REPORT_EXPORT: "report.export",
  RATE_PRIVATE_VIEW: "rate.private.view",
  RATE_PRIVATE_MANAGE: "rate.private.manage",
  EMPLOYEE_MANAGE: "employee.manage",
} as const;

export type PermissionCode = (typeof PermissionCode)[keyof typeof PermissionCode];

export const PERMISSION_LABELS: Record<PermissionCode, string> = {
  [PermissionCode.DASHBOARD_VIEW]: "Voir le dashboard",
  [PermissionCode.ENTRY_MANAGE]: "Gérer les entrées",
  [PermissionCode.TRANSFER_CREATE]: "Créer un envoi",
  [PermissionCode.PAYMENT_CREATE]: "Créer un paiement",
  [PermissionCode.OPERATION_VALIDATE]: "Valider une opération",
  [PermissionCode.WALLET_MANAGE]: "Gérer les wallets",
  [PermissionCode.NATIONAL_OPERATION_MANAGE]: "Effectuer des opérations nationales",
  [PermissionCode.COLLABORATION_MANAGE]: "Gérer les collaborations",
  [PermissionCode.SUPPLIER_MANAGE]: "Gérer les fournisseurs",
  [PermissionCode.CLIENT_MANAGE]: "Gérer les clients",
  [PermissionCode.REPORT_VIEW]: "Voir les rapports",
  [PermissionCode.REPORT_EXPORT]: "Exporter les données",
  [PermissionCode.RATE_PRIVATE_VIEW]: "Voir les taux privés",
  [PermissionCode.RATE_PRIVATE_MANAGE]: "Modifier les taux privés",
  [PermissionCode.EMPLOYEE_MANAGE]: "Gérer les employés",
};

export function hasPermission(
  permissions: string[],
  isOwner: boolean,
  isSuperAdmin: boolean,
  required: PermissionCode
): boolean {
  return isOwner || isSuperAdmin || permissions.includes(required);
}
