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

export function hasPermission(
  permissions: string[],
  isOwner: boolean,
  isSuperAdmin: boolean,
  required: PermissionCode
): boolean {
  return isOwner || isSuperAdmin || permissions.includes(required);
}
