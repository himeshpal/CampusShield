"use client";

import { CalendarClock, Loader2, Mail, Send, Siren, Webhook } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useNotificationSettings,
  useSaveNotificationSettings,
  useSendAlert,
} from "@/hooks/use-alerts";
import { SEVERITY, SEVERITY_ORDER } from "@/lib/alerts";
import { timeAgo } from "@/lib/format";
import type { AlertChannel, AlertSeverity, ChannelResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const CHANNELS: { key: AlertChannel; label: string; icon: typeof Mail; setup: string }[] = [
  {
    key: "email",
    label: "Email",
    icon: Mail,
    setup: "ALERT_EMAIL_TO and SMTP_* in .env (default: the Mailpit demo inbox on port 8025)",
  },
  {
    key: "telegram",
    label: "Telegram",
    icon: Send,
    setup: "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env",
  },
];

function ChannelState({ result }: { result?: ChannelResult }) {
  if (!result) return <span className="text-muted-foreground">No delivery reported yet</span>;
  if (result.ok) return <span>Delivered {timeAgo(result.at)}</span>;
  if (result.skipped) return <span className="text-muted-foreground">Not set up</span>;
  return (
    <span className="text-destructive" title={result.error ?? undefined}>
      Failed {timeAgo(result.at)}: {result.error}
    </span>
  );
}

export function NotificationsPanel({ isAdmin }: { isAdmin: boolean }) {
  const { data: settings } = useNotificationSettings();
  const save = useSaveNotificationSettings();
  const send = useSendAlert();
  if (!settings) return <Skeleton className="h-80 w-full rounded-xl" />;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Alert delivery</CardTitle>
          <CardDescription>
            Every scan is compared with the previous one. Alerts are kept here and pushed to n8n,
            which delivers them by email and Telegram.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="flex items-start gap-3">
            <Webhook className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div className="text-sm">
              <p className="font-medium">
                {settings.webhook_configured ? `n8n webhook (${settings.webhook_host})` : "n8n webhook not configured"}
              </p>
              <p className="text-muted-foreground">
                {settings.webhook_configured
                  ? "Signed with the shared secret from .env (N8N_WEBHOOK_SECRET)."
                  : "Set N8N_WEBHOOK_URL in .env and start the stack with -Automation."}
              </p>
            </div>
          </div>

          <ul className="space-y-3">
            {CHANNELS.map(({ key, label, icon: Icon, setup }) => {
              const result = settings.channels[key];
              return (
                <li key={key} className="flex items-start gap-3 text-sm">
                  <Icon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0">
                    <p className="flex items-center gap-2 font-medium">
                      {label}
                      <span
                        className={cn(
                          "size-2 rounded-full",
                          result?.ok ? "bg-primary" : result && !result.skipped ? "bg-destructive" : "bg-muted-foreground/30",
                        )}
                        aria-hidden
                      />
                    </p>
                    <p className="text-xs">
                      <ChannelState result={result} />
                    </p>
                    <p className="text-xs text-muted-foreground">Configured with {setup}.</p>
                  </div>
                </li>
              );
            })}
          </ul>

          {isAdmin && (
            <div className="flex flex-wrap items-center gap-3 border-t pt-4">
              <Button
                variant="outline"
                disabled={send.isPending}
                onClick={() =>
                  send.mutate("test", {
                    onSuccess: (r) =>
                      r.state === "sent"
                        ? toast.success("Test alert sent to n8n", {
                            description: "Delivery results appear here in a few seconds.",
                          })
                        : toast.error("Test alert not delivered", { description: r.error ?? r.state }),
                    onError: (e) => toast.error(e.message),
                  })
                }
              >
                {send.isPending ? <Loader2 className="animate-spin" /> : <Send />}
                Send test alert
              </Button>
              <p className="text-xs text-muted-foreground">Runs the whole path: backend → n8n → channels.</p>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>What gets pushed</CardTitle>
            <CardDescription>
              Lower-severity changes (e.g. a port closing) are still recorded on the Alerts page.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm font-medium">Minimum severity to notify</p>
            <Select
              value={settings.min_severity}
              disabled={!isAdmin || save.isPending}
              onValueChange={(v) =>
                save.mutate(v as AlertSeverity, {
                  onSuccess: () => toast.success("Notification threshold saved"),
                  onError: (e) => toast.error(e.message),
                })
              }
            >
              <SelectTrigger className="w-56" aria-label="Minimum severity to notify">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[...SEVERITY_ORDER].reverse().map((s) => (
                  <SelectItem key={s} value={s}>
                    {SEVERITY[s].label} and above
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Wazuh host monitoring</CardTitle>
            <CardDescription>
              The Wazuh agent on lab-pc-01 reports SSH attacks and file changes; the manager
              forwards level 5+ events here (stack.ps1 up -Siem).
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-start gap-3 text-sm">
            <Siren className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            {settings.wazuh ? (
              <div>
                <p className="font-medium">Last event {timeAgo(settings.wazuh.last_event_at)}</p>
                <p className="text-xs text-muted-foreground">
                  {settings.wazuh.last_rule} · agent {settings.wazuh.last_agent} ·{" "}
                  {settings.wazuh.events} events received
                </p>
              </div>
            ) : (
              <p className="text-muted-foreground">No event received yet. Start the SIEM profile to connect.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Scheduled scans</CardTitle>
            <CardDescription>Run by n8n with the service API key, shown as &ldquo;n8n&rdquo; in scan history.</CardDescription>
          </CardHeader>
          <CardContent className="flex items-start gap-3 text-sm">
            <CalendarClock className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <p className="text-muted-foreground">
              Daily standard audit at 07:00 (Asia/Kolkata) by default. Change it with
              SCAN_SCHEDULE_CRON and SCAN_SCHEDULE_PROFILE in .env; the workflows live in
              n8n/workflows and are loaded when n8n starts.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
