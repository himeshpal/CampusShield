export type Role = "admin" | "auditor";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
};

export type AuditEntry = {
  id: number;
  actor: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
};

export type Page<T> = { items: T[]; total: number };

export type Health = { status: string; database: string; nmap: string };

export type ScanProfileKey = "quick" | "standard" | "deep";
export type ScanStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export type ScanProfileOption = {
  key: ScanProfileKey;
  label: string;
  description: string;
  estimate: string;
  command: string;
};

export type ScanOptions = {
  profiles: ScanProfileOption[];
  authorized_subnets: string[];
  excluded: string[];
  default_target: string;
};

export type Scan = {
  id: number;
  target: string;
  profile: ScanProfileKey;
  status: ScanStatus;
  phase: string | null;
  progress: number;
  triggered_by: string;
  requested_by_name: string | null;
  hosts_up: number;
  open_ports: number;
  command: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type ScanPort = {
  port: number;
  protocol: string;
  service: string | null;
  product: string | null;
  version: string | null;
  extra_info: string | null;
  script_output: Record<string, string>;
};

export type ScanHost = {
  id: number;
  ip_address: string;
  mac_address: string | null;
  mac_vendor: string | null;
  hostname: string | null;
  os_guess: string | null;
  ports: ScanPort[];
};

export type ScanDetail = Scan & { hosts: ScanHost[] };
