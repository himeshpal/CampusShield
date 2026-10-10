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
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ActiveScanCard } from "@/components/scans/active-scan-card";
import { useCurrentUser } from "@/hooks/use-current-user";
import { useAssetSummary } from "@/hooks/use-assets";
import { useActiveScan, useScanHistory } from "@/hooks/use-scans";
import { cn } from "@/lib/utils";

type StatKey = "assets" | "unregistered" | "critical" | "alerts";

// "critical" and "alerts" get their values in the risk-scoring and alerting phases.
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
    tone: "text-risk-high",
    href: "/assets?status=unregistered",
  },
  {
    key: "critical",
    label: "Critical risk",
    icon: ShieldAlert,
    hint: "Assets scoring 75 or above",
    tone: "text-risk-critical",
  },
  { key: "alerts", label: "Open alerts", icon: Bell, hint: "Changes waiting for review" },
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
  const { user } = useCurrentUser();
  const { data: active } = useActiveScan();
  const { data: scans } = useScanHistory();
  const { data: inventory } = useAssetSummary();
  const values: Record<StatKey, number | undefined> = {
    assets: inventory?.registered,
    unregistered: inventory?.unregistered,
    critical: undefined,
    alerts: undefined,
  };
  const done: Record<StepKey, boolean> = {
    accounts: true,
    scan: !!scans?.some((s) => s.status === "completed"),
    inventory: !!inventory && inventory.registered > 0 && inventory.unregistered === 0,
    checklist: false,
    report: false,
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
          <Button asChild>
            <Link href="/scans">
              <Radar />
              Run network scan
            </Link>
          </Button>
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
          const alarming = key === "unregistered" && !!value;
          const card = (
            <Card
              className={cn(
                "h-full gap-3 transition-colors",
                href && "hover:border-primary/40",
                alarming && "border-risk-high/40 bg-risk-high/5",
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
                    alarming && "text-risk-high",
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
