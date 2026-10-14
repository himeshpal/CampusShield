import {
  ArrowUpRight,
  DoorClosed,
  DoorOpen,
  Info,
  OctagonAlert,
  ShieldAlert,
  ShieldMinus,
  ShieldQuestion,
  TrendingUp,
  WifiOff,
  type LucideIcon,
} from "lucide-react";

import type { AlertKind, AlertSeverity } from "@/lib/types";

/** Severities reuse the risk status colours for the three that need action; low and
 *  info stay neutral. Every badge shows the name and an icon, never colour alone. */
export const SEVERITY: Record<
  AlertSeverity,
  { label: string; mark: string; ink: string; tint: string; icon: LucideIcon }
> = {
  critical: { label: "Critical", mark: "bg-risk-critical", ink: "text-risk-critical-ink", tint: "border-risk-critical/40 bg-risk-critical/5", icon: OctagonAlert },
  high: { label: "High", mark: "bg-risk-high", ink: "text-risk-high-ink", tint: "border-risk-high/40 bg-risk-high/5", icon: ShieldAlert },
  medium: { label: "Medium", mark: "bg-risk-medium", ink: "text-risk-medium-ink", tint: "border-risk-medium/50 bg-risk-medium/5", icon: ShieldMinus },
  low: { label: "Low", mark: "bg-muted-foreground/50", ink: "text-muted-foreground", tint: "", icon: ShieldQuestion },
  info: { label: "Info", mark: "bg-muted-foreground/30", ink: "text-muted-foreground", tint: "", icon: Info },
};

export const SEVERITY_ORDER: AlertSeverity[] = ["critical", "high", "medium", "low", "info"];

export const KIND: Record<AlertKind, { label: string; icon: LucideIcon }> = {
  new_device: { label: "New device", icon: ShieldQuestion },
  host_missing: { label: "Not responding", icon: WifiOff },
  port_opened: { label: "Port opened", icon: DoorOpen },
  port_closed: { label: "Port closed", icon: DoorClosed },
  risk_jump: { label: "Risk rose", icon: TrendingUp },
  wazuh: { label: "Wazuh", icon: ArrowUpRight },
};
