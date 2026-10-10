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

export type MatchMethod = "mac" | "ip" | "new" | "ip_conflict";

export type ScanHost = {
  id: number;
  ip_address: string;
  mac_address: string | null;
  mac_vendor: string | null;
  hostname: string | null;
  os_guess: string | null;
  match_method: MatchMethod | null;
  asset: {
    id: number;
    asset_tag: string;
    name: string | null;
    status: AssetStatus;
    asset_type: AssetType;
  } | null;
  ports: ScanPort[];
};

export type ScanDetail = Scan & {
  hosts: ScanHost[];
  matched: number;
  new_devices: number;
  ip_conflicts: number;
};

export type AssetType =
  | "server"
  | "workstation"
  | "wifi_ap"
  | "iot_cctv"
  | "iot_biometric"
  | "printer"
  | "network_device"
  | "other";
export type AssetStatus = "registered" | "unregistered" | "retired";
export type CriticalityLevel = "low" | "medium" | "high";

export type ObservedPort = {
  port: number;
  protocol: string;
  service: string | null;
  product: string | null;
  version: string | null;
};

/** Fields an admin edits (create, update, register). */
export type AssetFields = {
  name: string;
  hostname: string | null;
  asset_type: AssetType;
  ip_address: string | null;
  mac_address: string | null;
  os_name: string | null;
  department: string | null;
  location: string | null;
  owner: string | null;
  notes: string | null;
  data_sensitivity: number;
  service_dependency: number;
  users_affected: number;
  replaceability: number;
  baseline_ports: number[];
};

export type Asset = Omit<AssetFields, "name"> & {
  id: number;
  asset_tag: string;
  name: string | null;
  status: AssetStatus;
  mac_vendor: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
  created_at: string;
  criticality: number;
  criticality_level: CriticalityLevel;
  observed_ports: ObservedPort[] | null;
  last_scan_id: number | null;
};

export type Observation = {
  scan_id: number;
  scanned_at: string;
  profile: ScanProfileKey;
  ip_address: string;
  match_method: MatchMethod | null;
  ports: ObservedPort[];
};

export type AssetDetail = Asset & { observations: Observation[] };

export type AssetSummary = {
  registered: number;
  unregistered: number;
  retired: number;
  by_type: Partial<Record<AssetType, number>>;
};
