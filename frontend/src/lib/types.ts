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
  alerts: number;
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
  findings: Finding[];
  risk_score: number | null;
  risk_band: RiskBand | null;
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
  risk_score: number | null;
  risk_band: RiskBand | null;
};

export type Observation = {
  scan_id: number;
  scanned_at: string;
  profile: ScanProfileKey;
  ip_address: string;
  match_method: MatchMethod | null;
  ports: ObservedPort[];
};

export type AssetDetail = Asset & {
  observations: Observation[];
  risk: RiskBreakdown | null;
  risk_history: RiskPoint[];
};

export type RiskBand = "low" | "medium" | "high" | "critical";

export type RiskItem = {
  kind: string;
  label: string;
  points: number;
  severity: string;
  port?: number;
  cve_id?: string;
  detail?: string;
};

export type RiskComponent = {
  key: "exposure" | "vulnerabilities" | "drift" | "controls" | "inventory";
  label: string;
  points: number;
  uncapped: number;
  cap: number;
  items: RiskItem[];
};

export type RiskBreakdown = {
  model_version: number;
  score: number;
  band: RiskBand;
  raw: number;
  criticality: number;
  multiplier: number;
  formula: string;
  components: RiskComponent[];
};

export type RiskPoint = { score: number; band: RiskBand; computed_at: string; scan_id: number | null };

export type Finding = {
  kind: string;
  severity: string;
  title: string;
  detail: string | null;
  port: number | null;
  cve_id: string | null;
  points: number;
};

export type RiskSummary = {
  bands: Record<RiskBand, number>;
  assessed: number;
  average: number | null;
  top: { id: number; asset_tag: string; name: string | null; status: AssetStatus; score: number; band: RiskBand }[];
  drivers: { key: string; label: string; points: number; share: number }[];
};

export type RiskModel = {
  version: number;
  formula: string;
  components: { key: string; label: string; cap: number; rule?: string }[];
  multiplier: string;
  bands: { band: RiskBand; from: number }[];
  cvss_points: { cvss_from: number; points: number }[];
  service_weights: { service: string; points: number; label: string }[];
  other_port_points: number;
  cves: { cve_id: string; product: string; version_spec: string; cvss: number; severity: string; summary: string }[];
  end_of_life: { product: string; version_spec: string; points: number; title: string }[];
  script_findings: { script: string; points: number; title: string }[];
  limitations: string[];
};

export type AssetSummary = {
  registered: number;
  unregistered: number;
  retired: number;
  by_type: Partial<Record<AssetType, number>>;
};

export type ControlStatus = "yes" | "no" | "na" | "unknown";

export type ChecklistItem = {
  id: number;
  key: string;
  label: string;
  description: string;
  points: number;
};

export type ChecklistEntry = {
  status: ControlStatus;
  evidence: string | null;
  updated_by: string | null;
  updated_at: string | null;
};

export type ChecklistRow = {
  asset_id: number;
  asset_tag: string;
  name: string | null;
  asset_type: AssetType;
  status: AssetStatus;
  risk_score: number | null;
  risk_band: RiskBand | null;
  entries: Record<string, ChecklistEntry>;
  answered: number;
};

export type ChecklistMatrix = { items: ChecklistItem[]; rows: ChecklistRow[] };

export type ChecklistSaveResult = {
  row: ChecklistRow;
  risk: {
    before: number | null;
    after: number | null;
    band_before: RiskBand | null;
    band_after: RiskBand | null;
  };
};

export type ChecklistSummary = {
  assets: number;
  answered: number;
  total: number;
  gaps: number;
  coverage: { key: string; label: string; counts: Record<ControlStatus, number> }[];
};

export type RiskTrendPoint = {
  at: string;
  average: number;
  assessed: number;
  bands: Record<RiskBand, number>;
};

export type ReportSummary = {
  assets: number;
  unregistered: number;
  assessed: number;
  average: number | null;
  average_band: RiskBand | null;
  bands: Record<RiskBand, number>;
  vulnerabilities: number;
  recommendations: number;
  checklist_answered: number;
  checklist_total: number;
  latest_scan_id: number | null;
};

export type Report = {
  id: number;
  number: string;
  title: string;
  include_details: boolean;
  summary: ReportSummary;
  pages: number;
  size_bytes: number;
  sha256: string;
  generated_by: string | null;
  created_at: string;
};

export type AlertSeverity = "info" | "low" | "medium" | "high" | "critical";
export type AlertStatus = "open" | "acknowledged" | "resolved";
export type AlertKind = "new_device" | "host_missing" | "port_opened" | "port_closed" | "risk_jump" | "wazuh";

export type ChannelResult = { ok: boolean; skipped?: boolean; at: string; error: string | null };
export type AlertChannel = "telegram" | "email";

export type Alert = {
  id: number;
  kind: AlertKind;
  severity: AlertSeverity;
  title: string;
  message: string;
  status: AlertStatus;
  asset: { id: number; asset_tag: string; name: string | null; status: AssetStatus } | null;
  scan_id: number | null;
  payload: Record<string, unknown>;
  delivery: {
    webhook?: "sent" | "failed" | "not_configured" | "below_threshold";
    channels?: Partial<Record<AlertChannel, ChannelResult>>;
  };
  delivered_at: string | null;
  delivery_error: string | null;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolved_by: string | null;
  resolved_at: string | null;
  resolution: string | null;
  created_at: string;
};

export type AlertSummary = {
  open: number;
  acknowledged: number;
  resolved: number;
  by_severity: Record<AlertSeverity, number>;
  by_kind: Partial<Record<AlertKind, number>>;
  latest_at: string | null;
};

export type NotificationSettings = {
  min_severity: AlertSeverity;
  webhook_configured: boolean;
  webhook_host: string | null;
  app_url: string;
  channels: Partial<Record<AlertChannel, ChannelResult>>;
  wazuh: { last_event_at: string; last_agent: string | null; last_rule: string | null; events: number } | null;
};
