export type CompanyStatus = "pending" | "active" | "suspended";

export type CompanyMe = {
  id: string;
  name: string;
  registration_code: string;
  address: string | null;
  phone: string;
  default_currency: string;
  status: CompanyStatus;
};

export type CollaboratorBalanceSummary = {
  collaboration_id: string;
  collaborator_company_id: string;
  currency: string;
  balance: string;
};

export type DashboardResponse = {
  wallets_balance_by_currency: Record<string, string>;
  collaborator_balances: CollaboratorBalanceSummary[];
  active_collaborations_count: number;
  entries_today_count: number;
  national_operations_today_count: number;
  transfers_today_count: number;
  transfers_pending_count: number;
  transfers_rejected_count: number;
  payments_today_count: number;
  payments_pending_count: number;
  payments_rejected_count: number;
  clients_total_balance: string;
  suppliers_total_balance: string;
  unread_notifications_count: number;
};

export type NotificationItem = {
  id: string;
  type: string;
  message: string;
  link_type: string | null;
  link_id: string | null;
  is_read: boolean;
  created_at: string;
};
