import { Badge } from "@/components/ui/badge";
import { assetType } from "@/lib/assets";
import type { AssetStatus, AssetType, CriticalityLevel, MatchMethod } from "@/lib/types";
import { cn } from "@/lib/utils";

const STATUS: Record<AssetStatus, { label: string; className: string; dot: string }> = {
  registered: { label: "Registered", className: "", dot: "bg-primary" },
  unregistered: {
    label: "Unregistered",
    className: "border-risk-high/40 bg-risk-high/10 text-risk-high",
    dot: "bg-risk-high animate-pulse",
  },
  retired: { label: "Retired", className: "text-muted-foreground", dot: "bg-muted-foreground" },
};

export function AssetStatusBadge({ status }: { status: AssetStatus }) {
  const s = STATUS[status];
  return (
    <Badge variant="outline" className={cn("gap-1.5", s.className)}>
      <span className={cn("size-1.5 rounded-full", s.dot)} />
      {s.label}
    </Badge>
  );
}

const CRITICALITY: Record<CriticalityLevel, string> = {
  low: "text-muted-foreground",
  medium: "border-risk-medium/40 text-risk-medium",
  high: "border-risk-critical/40 text-risk-critical",
};

export function CriticalityBadge({ level, total }: { level: CriticalityLevel; total: number }) {
  return (
    <Badge variant="outline" className={cn("gap-1 font-normal capitalize", CRITICALITY[level])}>
      <span className="font-medium">{level}</span>
      <span className="tabular-nums opacity-70">{total}/12</span>
    </Badge>
  );
}

export function AssetTypeLabel({ type, className }: { type: AssetType; className?: string }) {
  const t = assetType(type);
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <t.icon className="size-3.5 text-muted-foreground" />
      {t.label}
    </span>
  );
}

const MATCH: Record<MatchMethod, { label: string; className: string }> = {
  mac: { label: "Matched by MAC", className: "text-muted-foreground" },
  ip: { label: "Matched by IP", className: "text-muted-foreground" },
  new: { label: "New device", className: "border-risk-high/40 bg-risk-high/10 text-risk-high" },
  ip_conflict: {
    label: "IP conflict",
    className: "border-risk-critical/40 bg-risk-critical/10 text-risk-critical",
  },
};

export function MatchBadge({ method }: { method: MatchMethod }) {
  const m = MATCH[method];
  return (
    <Badge variant="outline" className={cn("font-normal", m.className)}>
      {m.label}
    </Badge>
  );
}
