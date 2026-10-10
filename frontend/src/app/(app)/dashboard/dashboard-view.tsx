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
import { useCurrentUser } from "@/hooks/use-current-user";

// Values arrive with the discovery, inventory and alerting phases.
const STATS: { label: string; icon: LucideIcon; hint: string; tone?: string }[] = [
  { label: "Total assets", icon: Server, hint: "Registered campus devices" },
  {
    label: "Unregistered devices",
    icon: ShieldAlert,
    hint: "Seen on the network, not in inventory",
    tone: "text-risk-high",
  },
  {
    label: "Critical risk",
    icon: ShieldAlert,
    hint: "Assets scoring 75 or above",
    tone: "text-risk-critical",
  },
  { label: "Open alerts", icon: Bell, hint: "Changes waiting for review" },
];

const STEPS: { title: string; text: string; href: string; icon: LucideIcon; done?: boolean }[] = [
  {
    title: "Sign in and secure accounts",
    text: "Admin and auditor roles, every action recorded in the audit log.",
    href: "/settings",
    icon: CheckCircle2,
    done: true,
  },
  {
    title: "Run the first network scan",
    text: "Discover live hosts, open ports and services on 172.25.0.0/24.",
    href: "/scans",
    icon: Radar,
  },
  {
    title: "Review the asset inventory",
    text: "Match hosts to registered assets and register unknown devices.",
    href: "/assets",
    icon: Server,
  },
  {
    title: "Complete the security checklist",
    text: "Record controls a scan cannot see: MFA, encryption, antivirus.",
    href: "/checklist",
    icon: ClipboardCheck,
  },
  {
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

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {STATS.map(({ label, icon: Icon, hint, tone }) => (
          <Card key={label} className="gap-3">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardDescription className="font-medium">{label}</CardDescription>
              <Icon className={`size-4 text-muted-foreground ${tone ?? ""}`} />
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold tracking-tight text-muted-foreground/60">—</p>
              <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
            </CardContent>
          </Card>
        ))}
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
              {STEPS.map(({ title, text, href, icon: Icon, done }) => (
                <li key={title}>
                  <Link
                    href={href}
                    className="group -mx-2 flex items-center gap-4 rounded-lg px-2 py-3 transition-colors hover:bg-muted/60"
                  >
                    <div
                      className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${
                        done ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                      }`}
                    >
                      <Icon className="size-4.5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{title}</p>
                      <p className="truncate text-xs text-muted-foreground">{text}</p>
                    </div>
                    {done ? (
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
