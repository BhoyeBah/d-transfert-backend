from enum import StrEnum


class PermissionCode(StrEnum):
    DASHBOARD_VIEW = "dashboard.view"
    ENTRY_MANAGE = "entry.manage"
    TRANSFER_CREATE = "transfer.create"
    PAYMENT_CREATE = "payment.create"
    OPERATION_VALIDATE = "operation.validate"
    WALLET_MANAGE = "wallet.manage"
    SUPPLIER_MANAGE = "supplier.manage"
    REPORT_VIEW = "report.view"
    REPORT_EXPORT = "report.export"
    RATE_PRIVATE_VIEW = "rate.private.view"
    RATE_PRIVATE_MANAGE = "rate.private.manage"
    EMPLOYEE_MANAGE = "employee.manage"


PERMISSION_DESCRIPTIONS: dict[PermissionCode, str] = {
    PermissionCode.DASHBOARD_VIEW: "Voir le dashboard",
    PermissionCode.ENTRY_MANAGE: "Gérer les entrées",
    PermissionCode.TRANSFER_CREATE: "Créer un envoi",
    PermissionCode.PAYMENT_CREATE: "Créer un paiement",
    PermissionCode.OPERATION_VALIDATE: "Valider une opération",
    PermissionCode.WALLET_MANAGE: "Gérer les wallets",
    PermissionCode.SUPPLIER_MANAGE: "Gérer les fournisseurs",
    PermissionCode.REPORT_VIEW: "Voir les rapports",
    PermissionCode.REPORT_EXPORT: "Exporter les données",
    PermissionCode.RATE_PRIVATE_VIEW: "Voir les taux privés",
    PermissionCode.RATE_PRIVATE_MANAGE: "Modifier les taux privés",
    PermissionCode.EMPLOYEE_MANAGE: "Gérer les employés",
}


class RoleCode(StrEnum):
    OWNER = "owner"
    EMPLOYEE = "employee"
    SUPER_ADMIN = "super_admin"
