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

// --- Wallets ---

export type WalletType = "cash" | "mobile_money" | "bank" | "other";
export type WalletStatus = "active" | "inactive";
export type MovementDirection = "in" | "out";

export type Wallet = {
  id: string;
  name: string;
  code: string;
  type: WalletType;
  phone: string | null;
  currency: string;
  balance: string;
  status: WalletStatus;
  description: string | null;
  created_at: string;
};

export type WalletMovement = {
  id: string;
  direction: MovementDirection;
  amount: string;
  currency: string;
  balance_before: string;
  balance_after: string;
  source_type: string;
  source_id: string;
  created_by_id: string;
  note: string | null;
  created_at: string;
};

// --- National operations ---

export type NationalOperationType = "deposit" | "withdrawal" | "exchange" | "rebalance" | "adjustment";
export type NationalOperationStatus = "draft" | "validated" | "cancelled" | "corrected";

export type NationalOperationLine = {
  wallet_id: string;
  amount_in: string;
  amount_out: string;
  currency: string;
  balance_before: string | null;
  balance_after: string | null;
  note: string | null;
};

export type NationalOperation = {
  id: string;
  reference: string;
  type: NationalOperationType;
  status: NationalOperationStatus;
  client_name: string | null;
  client_phone: string | null;
  note: string | null;
  proof_id: string | null;
  created_by_id: string;
  validated_at: string | null;
  cancelled_at: string | null;
  reversal_of_id: string | null;
  created_at: string;
  lines: NationalOperationLine[];
};

// --- Entries ---

export type EntryStatus =
  | "unallocated"
  | "partially_allocated"
  | "allocated"
  | "consumed"
  | "rejected"
  | "cancelled";

export type EntryLine = {
  wallet_id: string;
  amount: string;
  currency: string;
  note: string | null;
};

export type EntryAllocation = {
  target_type: "transfer" | "payment";
  target_id: string;
  currency: string;
  amount_allocated: string;
  created_at: string;
};

export type Entry = {
  id: string;
  reference: string;
  status: EntryStatus;
  client_name: string | null;
  client_phone: string | null;
  note: string | null;
  merged_into_id: string | null;
  created_by_id: string;
  created_at: string;
  lines: EntryLine[];
  allocations: EntryAllocation[];
  available_by_currency: Record<string, string>;
};

// --- Collaborations ---

export type CollaborationStatus = "pending" | "accepted" | "rejected" | "suspended" | "archived";
export type RateProposalStatus = "proposed" | "accepted" | "rejected";

export type Collaboration = {
  id: string;
  initiator_company_id: string;
  target_company_id: string;
  currency: string;
  status: CollaborationStatus;
  note: string | null;
  current_rate: string | null;
  created_at: string;
};

export type CollaborationRateHistoryEntry = {
  id: string;
  old_rate: string | null;
  new_rate: string;
  status: RateProposalStatus;
  proposed_by_company_id: string;
  decided_by_company_id: string | null;
  note: string | null;
  created_at: string;
  decided_at: string | null;
};

export type CollaboratorBalance = {
  collaboration_id: string;
  currency: string;
  balance: string;
};

export type PrivateRate = {
  id: string;
  collaboration_id: string | null;
  country: string | null;
  currency: string;
  rate: string;
  is_active: boolean;
  created_at: string;
  deactivated_at: string | null;
};

// --- Transfers ---

export type SendMode = "cash" | "wave" | "orange_money" | "bank" | "other";
export type TransferStatus = "pending" | "approved" | "rejected" | "cancelled";

export type Transfer = {
  id: string;
  reference: string;
  company_id: string;
  collaboration_id: string;
  entry_id: string | null;
  client_id: string | null;
  client_debt_amount: string | null;
  amount: string;
  currency: string;
  beneficiary_name: string | null;
  beneficiary_phone: string;
  send_mode: SendMode;
  note: string | null;
  private_rate_used: string | null;
  collaborative_rate_used: string;
  converted_amount: string;
  status: TransferStatus;
  proof_id: string | null;
  created_by_id: string;
  approved_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  created_at: string;
};

export type TransferStatusHistoryEntry = {
  id: string;
  old_status: TransferStatus | null;
  new_status: TransferStatus;
  company_id: string;
  reason: string | null;
  created_at: string;
};

// --- Payments ---

export type PaymentStatus = "pending" | "approved" | "rejected" | "cancelled";

export type Payment = {
  id: string;
  reference: string;
  company_id: string;
  collaboration_id: string;
  entry_id: string | null;
  wallet_id: string | null;
  client_id: string | null;
  client_debt_amount: string | null;
  amount: string;
  currency: string;
  client_name: string | null;
  client_phone: string | null;
  note: string | null;
  collaborative_rate_used: string;
  converted_amount: string;
  status: PaymentStatus;
  proof_id: string | null;
  created_by_id: string;
  approved_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  created_at: string;
};

export type PaymentStatusHistoryEntry = {
  id: string;
  old_status: PaymentStatus | null;
  new_status: PaymentStatus;
  company_id: string;
  reason: string | null;
  created_at: string;
};

// --- Clients ---

export type Client = {
  id: string;
  name: string;
  phone: string;
  note: string | null;
  balance: string;
  created_at: string;
};

export type ClientBalanceMovement = {
  id: string;
  source_type: string;
  source_id: string;
  delta: string;
  balance_before: string;
  balance_after: string;
  note: string | null;
  created_at: string;
};

// --- Suppliers ---

export type SupplierMovementType = "debt" | "payment";

export type Supplier = {
  id: string;
  name: string;
  code: string;
  phone: string | null;
  address: string | null;
  currency: string;
  note: string | null;
  balance: string;
  created_at: string;
};

export type SupplierBalanceMovement = {
  id: string;
  reference: string;
  type: SupplierMovementType;
  wallet_id: string;
  amount: string;
  balance_before: string;
  balance_after: string;
  proof_id: string | null;
  note: string | null;
  created_at: string;
};

// --- Employees ---

export type Employee = {
  id: string;
  matricule: string;
  full_name: string;
  phone: string;
  is_active: boolean;
  permissions: string[];
  created_at: string;
};

// --- Reports / Audit ---

export type DailyReport = {
  date: string;
  deposits_count: number;
  withdrawals_count: number;
  exchanges_count: number;
  rebalances_count: number;
  entries_count: number;
  entries_total_by_currency: Record<string, string>;
  transfers_created_count: number;
  transfers_approved_count: number;
  transfers_rejected_count: number;
  payments_created_count: number;
  payments_approved_count: number;
  payments_rejected_count: number;
};

export type AuditLogEntry = {
  id: string;
  company_id: string | null;
  user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  note: string | null;
  created_at: string;
};
