const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 31_536_000],
  ["month", 2_592_000],
  ["day", 86_400],
  ["hour", 3_600],
  ["minute", 60],
];

export function timeAgo(iso: string): string {
  const seconds = Math.round((new Date(iso).getTime() - Date.now()) / 1000);
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit);
  }
  return "just now";
}

export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]!.toUpperCase())
    .join("");
}

// Human wording for audit-log actions; unknown actions fall back to the raw key.
const ACTIONS: Record<string, string> = {
  "auth.login": "Signed in",
  "auth.logout": "Signed out",
  "auth.login_failed": "Failed sign-in attempt",
  "user.seeded": "Account created at first start",
  "user.created": "Created a user",
  "user.updated": "Updated a user",
  "user.deleted": "Deleted a user",
  "scan.started": "Started a network scan",
  "scan.completed": "Network scan completed",
  "scan.failed": "Network scan failed",
  "scan.cancelled": "Network scan cancelled",
  "scan.cancel_requested": "Cancelled a network scan",
  "asset.discovered": "Unregistered device discovered",
  "asset.seeded": "Demo asset registered",
  "asset.created": "Added an asset",
  "asset.updated": "Updated an asset",
  "asset.registered": "Registered a device",
  "asset.retired": "Retired an asset",
  "checklist.updated": "Updated the security checklist",
  "report.generated": "Generated an audit report",
  "report.deleted": "Deleted an audit report",
  "alert.raised": "Changes detected by a scan",
  "alert.acknowledged": "Acknowledged an alert",
  "alert.resolved": "Resolved an alert",
  "alert.test_sent": "Sent a test alert",
  "alert.delivery_failed": "Alert delivery failed",
  "settings.updated": "Changed a setting",
};

/** "226 KB" style file size. */
export function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** "1m 05s" style duration between two ISO timestamps (end defaults to now). */
export function duration(startIso: string | null, endIso?: string | null): string {
  if (!startIso) return "—";
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  const total = Math.max(0, Math.round((end - new Date(startIso).getTime()) / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return minutes ? `${minutes}m ${String(seconds).padStart(2, "0")}s` : `${seconds}s`;
}

/** "Apache httpd 2.4.49" from the parts nmap reports. */
export function softwareLabel(product: string | null, version: string | null): string | null {
  return [product, version].filter(Boolean).join(" ") || null;
}

export function actionLabel(action: string): string {
  return ACTIONS[action] ?? action;
}
