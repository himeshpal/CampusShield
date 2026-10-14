"use client";

import { BellRing, CheckCheck, Loader2, Settings2 } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

import { AlertItem } from "@/components/alerts/alert-item";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAlertAction, useAlerts, useAlertSummary, useNotificationSettings } from "@/hooks/use-alerts";
import { useCurrentUser } from "@/hooks/use-current-user";
import { useLiveRefresh } from "@/hooks/use-live-refresh";
import { KIND, SEVERITY, SEVERITY_ORDER } from "@/lib/alerts";
import { timeAgo } from "@/lib/format";
import type { AlertKind, AlertStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

type Tab = "unresolved" | AlertStatus | "all";
const TABS: { value: Tab; label: string }[] = [
  { value: "unresolved", label: "Needs review" },
  { value: "acknowledged", label: "Acknowledged" },
  { value: "resolved", label: "Resolved" },
  { value: "all", label: "All" },
];

export function AlertsView() {
  useLiveRefresh();
  const { user } = useCurrentUser();
  const isAdmin = user?.role === "admin";
  const router = useRouter();
  const params = useSearchParams();
  const tab = (TABS.find((t) => t.value === params.get("status"))?.value ?? "unresolved") as Tab;
  const kind = (params.get("kind") as AlertKind | null) ?? undefined;
  const focus = Number(params.get("focus")) || null;

  const { data: summary } = useAlertSummary();
  const { data: settings } = useNotificationSettings();
  const { data, isLoading } = useAlerts({
    unresolved: tab === "unresolved",
    status: tab === "acknowledged" || tab === "resolved" ? tab : undefined,
    kind,
    limit: 100,
  });
  const ackAll = useAlertAction();

  const setParam = (key: string, value: string | null) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("focus");
    router.replace(`/alerts${next.size ? `?${next}` : ""}`, { scroll: false });
  };

  // a link from Telegram / email: show that alert even if it is no longer unresolved
  const focusVisible = !!data?.items.some((a) => a.id === focus);
  useEffect(() => {
    if (focus && focusVisible) {
      document.getElementById(`alert-${focus}`)?.scrollIntoView({ block: "center" });
    }
  }, [focus, focusVisible]);
  useEffect(() => {
    if (focus && data && !focusVisible && tab !== "all") setParam("status", "all");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus, data, focusVisible, tab]);

  const unresolved = (summary?.open ?? 0) + (summary?.acknowledged ?? 0);

  return (
    <>
      <PageHeader
        title="Alerts"
        description="Changes detected between scans: new devices, opened ports, hosts that stopped responding, risk increases."
        actions={
          isAdmin && !!summary?.open && (
            <Button
              variant="outline"
              disabled={ackAll.isPending}
              onClick={() =>
                ackAll.mutate(
                  { type: "acknowledge-all" },
                  {
                    onSuccess: (n) => toast.success(`${n} alert${n === 1 ? "" : "s"} acknowledged`),
                    onError: (e) => toast.error(e.message),
                  },
                )
              }
            >
              {ackAll.isPending ? <Loader2 className="animate-spin" /> : <CheckCheck />}
              Acknowledge all ({summary.open})
            </Button>
          )
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="gap-2">
          <CardHeader>
            <CardDescription className="font-medium">Needs review</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold tabular-nums">{summary ? unresolved : "—"}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {summary ? `${summary.open} open · ${summary.acknowledged} acknowledged` : " "}
            </p>
          </CardContent>
        </Card>
        <Card className="gap-2 sm:col-span-1 xl:col-span-2">
          <CardHeader>
            <CardDescription className="font-medium">Unresolved by severity</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="grid grid-cols-3 gap-2 sm:grid-cols-5">
              {SEVERITY_ORDER.map((s) => {
                const Icon = SEVERITY[s].icon;
                const n = summary?.by_severity[s] ?? 0;
                return (
                  <li key={s} className="space-y-0.5">
                    <p className={cn("text-2xl font-semibold tabular-nums", n > 0 && SEVERITY[s].ink)}>
                      {summary ? n : "—"}
                    </p>
                    <p className="flex items-center gap-1 text-xs text-muted-foreground">
                      <span className={cn("size-2 rounded-full", SEVERITY[s].mark)} aria-hidden />
                      <Icon className="size-3" aria-hidden />
                      {SEVERITY[s].label}
                    </p>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>
        <Card className="gap-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardDescription className="font-medium">Notifications</CardDescription>
            <Link href="/settings?tab=notifications" aria-label="Notification settings">
              <Settings2 className="size-4 text-muted-foreground hover:text-foreground" />
            </Link>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {settings ? (
              <>
                <p className="flex items-center gap-2 font-medium">
                  <span
                    className={cn(
                      "size-2 rounded-full",
                      settings.webhook_configured ? "bg-primary" : "bg-muted-foreground/40",
                    )}
                  />
                  {settings.webhook_configured ? "n8n connected" : "n8n not configured"}
                </p>
                <p className="text-xs text-muted-foreground">
                  Pushes {SEVERITY[settings.min_severity].label.toLowerCase()} and above
                  {(["email", "telegram"] as const)
                    .filter((c) => settings.channels[c]?.ok)
                    .map((c) => (c === "email" ? " · email" : " · Telegram"))
                    .join("")}
                </p>
                {summary?.latest_at && (
                  <p className="text-xs text-muted-foreground">Last alert {timeAgo(summary.latest_at)}</p>
                )}
              </>
            ) : (
              <Skeleton className="h-10 w-full" />
            )}
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Tabs value={tab} onValueChange={(v) => setParam("status", v === "unresolved" ? null : v)}>
          <TabsList>
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <Select value={kind ?? "any"} onValueChange={(v) => setParam("kind", v === "any" ? null : v)}>
          <SelectTrigger className="w-full sm:w-48" aria-label="Alert type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">All types</SelectItem>
            {(Object.keys(KIND) as AlertKind[])
              .filter((k) => k !== "wazuh")
              .map((k) => (
                <SelectItem key={k} value={k}>
                  {KIND[k].label}
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      </div>

      <div className="mt-4">
        {isLoading && (
          <div className="space-y-3">
            {Array.from({ length: 3 }, (_, i) => (
              <Skeleton key={i} className="h-24 w-full rounded-lg" />
            ))}
          </div>
        )}
        {data?.items.length === 0 && (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed py-14 text-center">
            <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <BellRing className="size-6" />
            </div>
            <div>
              <p className="font-medium">
                {tab === "unresolved" ? "Nothing needs review" : "No alerts here"}
              </p>
              <p className="max-w-md text-sm text-muted-foreground">
                Every scan is compared with the one before it. New devices, opened ports, hosts
                that stop responding and risk increases appear here and are pushed to n8n.
              </p>
            </div>
          </div>
        )}
        <ul className="space-y-3">
          {data?.items.map((alert) => (
            <AlertItem key={alert.id} alert={alert} canAct={isAdmin} focused={alert.id === focus} />
          ))}
        </ul>
        {data && data.total > data.items.length && (
          <p className="mt-3 text-center text-xs text-muted-foreground">
            Showing the newest {data.items.length} of {data.total}.
          </p>
        )}
      </div>
    </>
  );
}
