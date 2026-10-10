"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  ChevronDown,
  Clock,
  Copy,
  Cpu,
  Network,
  Server,
  SlidersHorizontal,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { MatchBadge } from "@/components/assets/asset-badges";
import { RiskBadge } from "@/components/risk/risk-badge";
import { ActiveScanCard } from "@/components/scans/active-scan-card";
import { PROFILE_LABELS, ScanStatusBadge } from "@/components/scans/scan-status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCurrentUser } from "@/hooks/use-current-user";
import { useActiveScan } from "@/hooks/use-scans";
import { api, ApiError } from "@/lib/api";
import { dateTime, duration, softwareLabel } from "@/lib/format";
import type { ScanDetail, ScanHost } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ScanDetailView() {
  const { id } = useParams<{ id: string }>();
  const scanId = Number(id);
  const { user } = useCurrentUser();
  useActiveScan(); // announces completion and refreshes this page's data

  const { data: scan, error, isLoading } = useQuery({
    queryKey: ["scans", "detail", scanId],
    queryFn: () => api<ScanDetail>(`/scans/${scanId}`),
    refetchInterval: (q) =>
      q.state.data && ["queued", "running"].includes(q.state.data.status) ? 1500 : false,
  });

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="py-16 text-center">
        <p className="font-medium">Scan #{id} does not exist.</p>
        <Button asChild variant="link">
          <Link href="/scans">Back to scans</Link>
        </Button>
      </div>
    );
  }

  const running = scan && ["queued", "running"].includes(scan.status);

  return (
    <>
      <Link
        href="/scans"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Network scans
      </Link>

      <div className="mb-6 flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight">Scan #{id}</h1>
          {scan && <ScanStatusBadge status={scan.status} />}
        </div>
        {isLoading || !scan ? (
          <Skeleton className="h-4 w-80" />
        ) : (
          <p className="text-sm text-muted-foreground">
            <span className="font-mono">{scan.target}</span> · {PROFILE_LABELS[scan.profile]}{" "}
            profile · started {dateTime(scan.created_at)}
            {scan.requested_by_name && ` by ${scan.requested_by_name}`}
          </p>
        )}
      </div>

      {scan && running && (
        <div className="mb-6">
          <ActiveScanCard scan={scan} canCancel={user?.role === "admin"} />
        </div>
      )}

      {scan?.status === "failed" && (
        <div className="mb-6 flex gap-3 rounded-xl border border-risk-critical/30 bg-risk-critical/5 p-4 text-sm">
          <AlertTriangle className="size-5 shrink-0 text-risk-critical-ink" />
          <div>
            <p className="font-medium">The scan did not complete</p>
            <p className="mt-0.5 break-all text-muted-foreground">{scan.error}</p>
          </div>
        </div>
      )}

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat icon={Server} label="Hosts up" value={scan?.status === "completed" ? scan.hosts_up : "—"} />
        <Stat
          icon={Network}
          label="Open ports"
          value={scan?.status === "completed" ? scan.open_ports : "—"}
        />
        <Stat
          icon={Clock}
          label="Duration"
          value={scan?.finished_at ? duration(scan.started_at, scan.finished_at) : "—"}
        />
        <Stat
          icon={SlidersHorizontal}
          label="Profile"
          value={scan ? PROFILE_LABELS[scan.profile] : "—"}
        />
      </div>

      {scan?.command && <CommandCard command={scan.command} />}

      {scan?.status === "completed" && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Discovered hosts</CardTitle>
            <CardDescription>
              {scan.hosts.length} live hosts · {scan.matched} matched to the inventory
              {scan.new_devices > 0 && (
                <span className="font-medium text-risk-high-ink">
                  {" "}
                  · {scan.new_devices} new {scan.new_devices === 1 ? "device" : "devices"}
                </span>
              )}
              {scan.ip_conflicts > 0 && (
                <span className="font-medium text-risk-critical-ink">
                  {" "}
                  · {scan.ip_conflicts} IP {scan.ip_conflicts === 1 ? "conflict" : "conflicts"}
                </span>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {scan.hosts.map((host) => (
              <HostRow key={host.id} host={host} />
            ))}
          </CardContent>
        </Card>
      )}
    </>
  );
}

function Stat({ icon: Icon, label, value }: { icon: LucideIcon; label: string; value: string | number }) {
  return (
    <Card className="gap-2 py-4">
      <CardContent className="flex items-center gap-3">
        <div className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
          <Icon className="size-4" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold tabular-nums">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function CommandCard({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="flex items-start gap-2 rounded-xl border bg-muted/40 p-3">
      <code className="flex-1 font-mono text-xs leading-relaxed break-all text-muted-foreground">
        <span className="select-none text-primary">$ </span>
        {command}
      </code>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label="Copy command"
        onClick={() => {
          navigator.clipboard.writeText(command);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        }}
      >
        {copied ? <Check className="text-primary" /> : <Copy />}
      </Button>
    </div>
  );
}

const SEVERITY: Record<string, { label: string; dot: string }> = {
  critical: { label: "Critical", dot: "bg-risk-critical" },
  high: { label: "High", dot: "bg-risk-high" },
  medium: { label: "Medium", dot: "bg-risk-medium" },
  low: { label: "Low", dot: "bg-muted-foreground/50" }, // not green: low severity is not "fine"
};

function SeverityTag({ severity }: { severity: string }) {
  const s = SEVERITY[severity] ?? SEVERITY.low!;
  return (
    <span className="mt-0.5 inline-flex w-18 shrink-0 items-center gap-1.5 text-xs text-muted-foreground">
      <span className={cn("size-2 rounded-full", s.dot)} aria-hidden />
      {s.label}
    </span>
  );
}

/** Which inventory record this host was matched to (or that it is a new device). */
function HostAssetLine({ host }: { host: ScanHost }) {
  if (!host.asset) return null;
  const isNew = host.match_method === "new" || host.match_method === "ip_conflict";
  const unregistered = host.asset.status === "unregistered";
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
      <Link
        href={`/assets/${host.asset.id}`}
        className={cn(
          "text-xs font-medium hover:underline",
          unregistered ? "text-risk-high-ink" : "text-primary",
        )}
      >
        {host.asset.asset_tag}
        {host.asset.name ? ` · ${host.asset.name}` : unregistered ? " · Unregistered" : ""}
      </Link>
      {isNew && host.match_method && <MatchBadge method={host.match_method} />}
      {!isNew && unregistered && (
        <Badge variant="outline" className="border-risk-high/40 font-normal text-risk-high-ink">
          Still unregistered
        </Badge>
      )}
    </div>
  );
}

function HostRow({ host }: { host: ScanHost }) {
  const [open, setOpen] = useState(false);
  const scripts = host.ports.flatMap((p) =>
    Object.entries(p.script_output).map(([name, output]) => ({ port: p.port, name, output })),
  );

  return (
    <div className="rounded-lg border">
      {/* identity block and toggle are siblings: the asset link must not sit inside a button */}
      <div className="flex flex-col sm:flex-row sm:items-center">
        <div className="min-w-0 px-4 pt-4 sm:w-72 sm:shrink-0 sm:py-4">
          <p className="font-mono text-sm font-semibold">{host.ip_address}</p>
          <p className="truncate text-xs text-muted-foreground" title={host.mac_vendor ?? undefined}>
            {host.mac_vendor ?? "Unknown vendor"}
          </p>
          {host.mac_address && (
            <p className="font-mono text-[11px] text-muted-foreground/80">{host.mac_address}</p>
          )}
          <HostAssetLine host={host} />
        </div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex flex-1 flex-col gap-3 self-stretch p-4 text-left transition-colors hover:bg-muted/40 sm:flex-row sm:items-center"
        aria-expanded={open}
        aria-label={`${open ? "Hide" : "Show"} port details for ${host.ip_address}`}
      >
        <div className="flex flex-1 flex-wrap gap-1.5">
          {host.ports.length === 0 && (
            <span className="text-xs text-muted-foreground">No open ports in this profile</span>
          )}
          {host.ports.map((p) => (
            <Badge key={`${p.protocol}${p.port}`} variant="secondary" className="font-mono font-normal">
              {p.port}
              {p.service && <span className="text-muted-foreground">/{p.service}</span>}
            </Badge>
          ))}
        </div>
        {host.risk_score !== null && (
          <RiskBadge score={host.risk_score} band={host.risk_band} className="shrink-0" />
        )}
        {host.os_guess && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground">
            <Cpu className="size-3.5" />
            {host.os_guess}
          </span>
        )}
        <ChevronDown
          className={cn("size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")}
        />
      </button>
      </div>

      {open && (
        <div className="border-t px-4 pb-4">
          {host.findings.length > 0 && (
            <div className="mt-4 space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">
                Findings ({host.findings.length})
              </p>
              <ul className="divide-y rounded-md border">
                {host.findings.map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 px-3 py-2 text-sm">
                    <SeverityTag severity={f.severity} />
                    <div className="min-w-0 flex-1">
                      <p>{f.title}</p>
                      {f.detail && <p className="text-xs text-muted-foreground">{f.detail}</p>}
                    </div>
                    <span className="shrink-0 text-xs font-medium tabular-nums">+{f.points}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">Port</TableHead>
                <TableHead className="w-28">Service</TableHead>
                <TableHead>Software</TableHead>
                <TableHead>Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {host.ports.map((p) => (
                <TableRow key={`${p.protocol}${p.port}`}>
                  <TableCell className="font-mono">
                    {p.port}/{p.protocol}
                  </TableCell>
                  <TableCell>{p.service ?? "—"}</TableCell>
                  <TableCell className="font-medium">
                    {softwareLabel(p.product, p.version) ?? (
                      <span className="font-normal text-muted-foreground">Not identified</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{p.extra_info ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {scripts.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="text-xs font-medium text-muted-foreground">NSE script findings</p>
              {scripts.map((s) => (
                <div key={`${s.port}-${s.name}`} className="rounded-md bg-muted/60 p-3">
                  <p className="mb-1 font-mono text-xs font-semibold">
                    {s.name} <span className="font-normal text-muted-foreground">· port {s.port}</span>
                  </p>
                  <pre className="max-h-40 overflow-auto font-mono text-xs whitespace-pre-wrap text-muted-foreground">
                    {s.output}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
