"use client";

import {
  ArrowRight,
  Bell,
  CheckCircle2,
  Circle,
  ClipboardCheck,
  FileText,
  Radar,
  Server,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";

import { ActivityFeed } from "@/components/activity-feed";
import { CampusTrend } from "@/components/risk/campus-trend";
import { PageHeader } from "@/components/page-header";
import { RiskBadge } from "@/components/risk/risk-badge";
import { RiskDistribution } from "@/components/risk/risk-distribution";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ActiveScanCard } from "@/components/scans/active-scan-card";
import { useCurrentUser } from "@/hooks/use-current-user";
import { useAlertSummary } from "@/hooks/use-alerts";
import { useAssetSummary, useRiskSummary, useRiskTrend } from "@/hooks/use-assets";
import { useChecklistSummary } from "@/hooks/use-checklist";
import { useLiveRefresh } from "@/hooks/use-live-refresh";
import { reportPdfUrl, useReports } from "@/hooks/use-reports";
import { useActiveScan, useScanHistory } from "@/hooks/use-scans";
import { PROFILE_LABELS } from "@/components/scans/scan-status-badge";
import { timeAgo } from "@/lib/format";
import { cn } from "@/lib/utils";

type StatKey = "assets" | "unregistered" | "critical" | "alerts";

const STATS: {
  key: StatKey;
  label: string;
  icon: LucideIcon;
  hint: string;
  tone?: string;
  href?: string;
}[] = [
  { key: "assets", label: "Total assets", icon: Server, hint: "Registered campus devices", href: "/assets" },
  {
    key: "unregistered",
    label: "Unregistered devices",
    icon: ShieldAlert,
    hint: "Seen on the network, not in inventory",
    tone: "text-risk-high-ink",
    href: "/assets?status=unregistered",
  },
  {
    key: "critical",
    label: "Critical risk",
    icon: ShieldAlert,
    hint: "Assets scoring 75 or above",
    tone: "text-risk-critical-ink",
    href: "/assets",
  },
  {
    key: "alerts",
    label: "Open alerts",
    icon: Bell,
    hint: "Changes waiting for review",
    tone: "text-risk-high-ink",
    href: "/alerts",
  },
];

type StepKey = "accounts" | "scan" | "inventory" | "checklist" | "report";

const STEPS: { key: StepKey; title: string; text: string; href: string; icon: LucideIcon }[] = [
  {
    key: "accounts",
    title: "Sign in and secure accounts",
    text: "Admin and auditor roles, every action recorded in the audit log.",
    href: "/settings",
    icon: CheckCircle2,
  },
  {
    key: "scan",
    title: "Run the first network scan",
    text: "Discover live hosts, open ports and services on 172.25.0.0/24.",
    href: "/scans",
    icon: Radar,
  },
  {
    key: "inventory",
    title: "Review the asset inventory",
    text: "Match hosts to registered assets and register unknown devices.",
    href: "/assets",
    icon: Server,
  },
  {
    key: "checklist",
    title: "Complete the security checklist",
    text: "Record controls a scan cannot see: MFA, encryption, antivirus.",
    href: "/checklist",
    icon: ClipboardCheck,
  },
  {
    key: "report",
    title: "Generate the audit report",
    text: "Export a PDF summary of campus security posture.",
    href: "/reports",
    icon: FileText,
  },
];

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function DashboardView() {
  useLiveRefresh();
  const { user } = useCurrentUser();
  const { data: active } = useActiveScan();
  const { data: scans } = useScanHistory();
  const { data: inventory } = useAssetSummary();
  const { data: risk } = useRiskSummary();
  const { data: checklist } = useChecklistSummary();
  const { data: trend } = useRiskTrend();
  const { data: alerts } = useAlertSummary();
  const { data: reports } = useReports();
  const lastScan = scans?.find((s) => s.status === "completed");
  const lastReport = reports?.[0];
  const values: Record<StatKey, number | undefined> = {
    assets: inventory?.registered,
    unregistered: inventory?.unregistered,
    critical: risk?.bands.critical,
    alerts: alerts?.open,
  };
  const done: Record<StepKey, boolean> = {
    accounts: true,
    scan: !!scans?.some((s) => s.status === "completed"),
    inventory: !!inventory && inventory.registered > 0 && inventory.unregistered === 0,
    checklist: !!checklist && checklist.total > 0 && checklist.answered === checklist.total,
    report: !!reports?.length,
  };

  return (
    <>
      <PageHeader
        title="Security overview"
        description={
          user
            ? `${greeting()}, ${user.full_name}. Here is the campus-wide security posture.`
            : "Campus-wide security posture at a glance."
        }
        actions={
          <>
            <span
              className="mr-2 hidden items-center gap-1.5 text-xs text-muted-foreground sm:flex"
              title="The overview refreshes itself every 30 seconds"
            >
              <span className="relative flex size-2">
                <span className="absolute inline-flex size-full rounded-full motion-safe:animate-ping bg-primary/60" />
                <span className="relative inline-flex size-2 rounded-full bg-primary" />
              </span>
              Live
            </span>
            <Button asChild>
              <Link href="/scans">
                <Radar />
                Run network scan
              </Link>
            </Button>
          </>
        }
      />

      {active && (
        <div className="mb-6">
          <ActiveScanCard scan={active} canCancel={user?.role === "admin"} />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {STATS.map(({ key, label, icon: Icon, hint, tone, href }) => {
          const value = values[key];
          const alarming = (key === "unregistered" || key === "critical" || key === "alerts") && !!value;
          const card = (
            <Card
              className={cn(
                "h-full gap-3 transition-colors",
                href && "hover:border-primary/40",
                alarming && key !== "critical" && "border-risk-high/40 bg-risk-high/5",
                alarming && key === "critical" && "border-risk-critical/40 bg-risk-critical/5",
              )}
            >
              <CardHeader className="flex flex-row items-center justify-between">
                <CardDescription className="font-medium">{label}</CardDescription>
                <Icon className={cn("size-4 text-muted-foreground", tone)} />
              </CardHeader>
              <CardContent>
                <p
                  className={cn(
                    "text-3xl font-semibold tracking-tight tabular-nums",
                    value === undefined && "text-muted-foreground/60",
                    alarming && (key === "critical" ? "text-risk-critical-ink" : "text-risk-high-ink"),
                  )}
                >
                  {value ?? "—"}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
              </CardContent>
            </Card>
          );
          return href ? (
            <Link key={key} href={href} aria-label={`${label}: ${value ?? "unknown"}`}>
              {card}
            </Link>
          ) : (
            <div key={key}>{card}</div>
          );
        })}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div className="space-y-1.5">
              <CardTitle>Risk distribution</CardTitle>
              <CardDescription>
                {risk?.assessed ? `${risk.assessed} assets assessed` : "No assets assessed yet"}
              </CardDescription>
            </div>
            {risk?.average != null && (
              <div className="text-right">
                <p className="text-2xl font-semibold tabular-nums">{Math.round(risk.average)}</p>
                <p className="text-xs text-muted-foreground">average score</p>
              </div>
            )}
          </CardHeader>
          <CardContent>
            {risk ? <RiskDistribution bands={risk.bands} /> : <Skeleton className="h-16 w-full" />}
            {!!risk?.drivers.length && (
              <div className="mt-6 space-y-2.5 border-t pt-4">
                <p className="text-sm font-medium">What drives the risk</p>
                {risk.drivers
                  .filter((d) => d.points > 0)
                  .map((d) => (
                    <div key={d.key} className="grid grid-cols-[minmax(0,13rem)_1fr_3rem] items-center gap-3 text-sm">
                      <span className="truncate text-muted-foreground">{d.label}</span>
                      {/* neutral fill: an amount, not a status */}
                      <div className="h-2 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-foreground/60" style={{ width: `${d.share * 100}%` }} />
                      </div>
                      <span className="text-right tabular-nums">{Math.round(d.share * 100)}%</span>
                    </div>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Riskiest assets</CardTitle>
            <CardDescription>Fix these first.</CardDescription>
          </CardHeader>
          <CardContent>
            {risk?.top.length === 0 && (
              <p className="text-sm text-muted-foreground">Run a scan to assess assets.</p>
            )}
            <ol className="space-y-1">
              {risk?.top.map((a, i) => (
                <li key={a.id}>
                  <Link
                    href={`/assets/${a.id}`}
                    className="-mx-2 flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors hover:bg-muted/60"
                  >
                    <span className="w-4 text-xs tabular-nums text-muted-foreground">{i + 1}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">
                        {a.name ?? (a.status === "unregistered" ? "Unknown device" : a.asset_tag)}
                      </p>
                      <p className="font-mono text-xs text-muted-foreground">{a.asset_tag}</p>
                    </div>
                    <RiskBadge score={a.score} band={a.band} />
                  </Link>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Campus risk over time</CardTitle>
            <CardDescription>Average score after every scan and checklist update</CardDescription>
          </CardHeader>
          <CardContent>
            {!trend ? (
              <Skeleton className="h-52 w-full" />
            ) : trend.length < 2 ? (
              <p className="flex h-52 items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">
                The trend appears after the second scoring event.
              </p>
            ) : (
              <CampusTrend points={trend} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Audit status</CardTitle>
            <CardDescription>Where the evidence for the next report stands</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-start gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <Radar className="size-4.5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">Latest scan</p>
                {lastScan ? (
                  <p className="text-xs text-muted-foreground">
                    <Link href={`/scans/${lastScan.id}`} className="hover:underline">
                      #{lastScan.id}
                    </Link>{" "}
                    · {PROFILE_LABELS[lastScan.profile]} · {timeAgo(lastScan.finished_at ?? lastScan.created_at)} ·{" "}
                    {lastScan.hosts_up} hosts
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground">No completed scan yet</p>
                )}
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <ClipboardCheck className="size-4.5" />
              </div>
              <div className="min-w-0 flex-1 space-y-1.5">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="text-sm font-medium">Security checklist</p>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {checklist ? `${checklist.answered} / ${checklist.total}` : "—"}
                  </span>
                </div>
                <Progress
                  value={checklist?.total ? (100 * checklist.answered) / checklist.total : 0}
                  aria-label="Checklist answers recorded"
                />
                <p className="text-xs text-muted-foreground">
                  {checklist?.gaps ? `${checklist.gaps} controls recorded as missing` : "Answers recorded so far"}
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <FileText className="size-4.5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">Latest report</p>
                {lastReport ? (
                  <p className="truncate text-xs text-muted-foreground">
                    <a href={reportPdfUrl(lastReport.id)} target="_blank" rel="noopener" className="hover:underline">
                      {lastReport.number}
                    </a>{" "}
                    · {timeAgo(lastReport.created_at)} · {lastReport.pages} pages
                  </p>
                ) : (
                  <p className="text-xs text-muted-foreground">No report generated yet</p>
                )}
              </div>
              <Button asChild variant="outline" size="sm">
                <Link href="/reports">{lastReport ? "Reports" : "Generate"}</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Getting started</CardTitle>
            <CardDescription>
              The audit workflow, from first scan to the report for the institution.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ol className="divide-y">
              {STEPS.map(({ key, title, text, href, icon: Icon }) => (
                <li key={key}>
                  <Link
                    href={href}
                    className="group -mx-2 flex items-center gap-4 rounded-lg px-2 py-3 transition-colors hover:bg-muted/60"
                  >
                    <div
                      className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${
                        done[key] ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                      }`}
                    >
                      <Icon className="size-4.5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{title}</p>
                      <p className="truncate text-xs text-muted-foreground">{text}</p>
                    </div>
                    {done[key] ? (
                      <span className="text-xs font-medium text-primary">Done</span>
                    ) : (
                      <>
                        <Circle className="size-4 text-muted-foreground/40 group-hover:hidden" />
                        <ArrowRight className="hidden size-4 text-muted-foreground group-hover:block" />
                      </>
                    )}
                  </Link>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <CardDescription>From the audit log</CardDescription>
          </CardHeader>
          <CardContent>
            <ActivityFeed />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
