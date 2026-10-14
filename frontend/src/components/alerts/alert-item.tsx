"use client";

import { Check, CheckCheck, Loader2, Mail, Send, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAlertAction } from "@/hooks/use-alerts";
import { KIND, SEVERITY } from "@/lib/alerts";
import { dateTime, timeAgo } from "@/lib/format";
import type { Alert, AlertChannel, AlertSeverity, ChannelResult } from "@/lib/types";
import { cn } from "@/lib/utils";

export function SeverityBadge({ severity }: { severity: AlertSeverity }) {
  const s = SEVERITY[severity];
  return (
    <Badge variant="outline" className="gap-1.5 font-normal">
      <span className={cn("size-2 rounded-full", s.mark)} aria-hidden />
      <span className="font-medium">{s.label}</span>
    </Badge>
  );
}

const CHANNEL: Record<AlertChannel, { label: string; icon: typeof Mail }> = {
  email: { label: "Email", icon: Mail },
  telegram: { label: "Telegram", icon: Send },
};

function ChannelChip({ channel, result }: { channel: AlertChannel; result: ChannelResult }) {
  const { label, icon: Icon } = CHANNEL[channel];
  const state = result.ok ? "sent" : result.skipped ? "not set up" : "failed";
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex items-center gap-1",
            result.ok ? "text-foreground/80" : result.skipped ? "text-muted-foreground/70" : "text-destructive",
          )}
        >
          <Icon className="size-3" />
          {label} {state}
          {result.ok ? <Check className="size-3" /> : !result.skipped && <X className="size-3" />}
        </span>
      </TooltipTrigger>
      <TooltipContent>
        {result.error ?? `Delivered ${dateTime(result.at)}`}
      </TooltipContent>
    </Tooltip>
  );
}

function Delivery({ alert }: { alert: Alert }) {
  const { webhook, channels } = alert.delivery;
  if (channels && Object.keys(channels).length) {
    return (
      <>
        {(Object.entries(channels) as [AlertChannel, ChannelResult][]).map(([c, r]) => (
          <ChannelChip key={c} channel={c} result={r} />
        ))}
      </>
    );
  }
  if (!webhook) return null;
  const text = {
    sent: "Sent to n8n",
    failed: "n8n unreachable",
    not_configured: "n8n not configured",
    below_threshold: "Not pushed (below threshold)",
  }[webhook];
  return (
    <span className={cn(webhook === "failed" && "text-destructive")} title={alert.delivery_error ?? undefined}>
      {text}
    </span>
  );
}

/** Rule, how often it fired and the attacking device, for alerts from the Wazuh agent. */
function WazuhFacts({ alert }: { alert: Alert }) {
  const p = alert.payload as {
    rule_id?: string;
    level?: number;
    count?: number;
    mitre?: string[];
    srcip?: string;
    source_asset_id?: number | null;
  };
  return (
    <p className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
      <span>
        Wazuh rule {p.rule_id} · level {p.level}
      </span>
      {(p.count ?? 1) > 1 && <span className="font-medium text-foreground/80">{p.count} events</span>}
      {!!p.mitre?.length && <span>MITRE ATT&amp;CK {p.mitre.join(", ")}</span>}
      {p.srcip &&
        (p.source_asset_id ? (
          <Link href={`/assets/${p.source_asset_id}`} className="hover:underline">
            from {p.srcip}
          </Link>
        ) : (
          <span>from {p.srcip}</span>
        ))}
    </p>
  );
}

export function AlertItem({
  alert,
  canAct,
  focused,
  compact,
}: {
  alert: Alert;
  canAct: boolean;
  focused?: boolean;
  compact?: boolean;
}) {
  const action = useAlertAction();
  const [resolving, setResolving] = useState(false);
  const kind = KIND[alert.kind];
  const KindIcon = kind.icon;
  const resolved = alert.status === "resolved";

  return (
    <li
      id={`alert-${alert.id}`}
      className={cn(
        "flex gap-3 rounded-lg border p-3 transition-colors sm:gap-4 sm:p-4",
        !resolved && SEVERITY[alert.severity].tint,
        resolved && "bg-muted/20",
        focused && "ring-2 ring-primary/50",
      )}
    >
      <div
        className={cn(
          "flex size-9 shrink-0 items-center justify-center rounded-lg bg-background",
          resolved ? "text-muted-foreground" : SEVERITY[alert.severity].ink,
        )}
      >
        <KindIcon className="size-4.5" />
      </div>

      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={alert.severity} />
          <span className="text-xs text-muted-foreground">{kind.label}</span>
          {alert.status === "acknowledged" && (
            <Badge variant="secondary" className="font-normal">Acknowledged</Badge>
          )}
          {resolved && (
            <Badge variant="secondary" className="gap-1 font-normal">
              <CheckCheck className="size-3" /> Resolved
            </Badge>
          )}
        </div>
        <p className={cn("text-sm font-medium", resolved && "text-muted-foreground")}>{alert.title}</p>
        {alert.kind === "wazuh" && <WazuhFacts alert={alert} />}
        {!compact && <p className="text-sm text-muted-foreground">{alert.message}</p>}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span title={dateTime(alert.created_at)}>{timeAgo(alert.created_at)}</span>
          {alert.asset && (
            <Link href={`/assets/${alert.asset.id}`} className="font-mono hover:underline">
              {alert.asset.asset_tag}
            </Link>
          )}
          {alert.scan_id && !compact && (
            <Link href={`/scans/${alert.scan_id}`} className="hover:underline">
              scan #{alert.scan_id}
            </Link>
          )}
          {!compact && <Delivery alert={alert} />}
        </div>
        {(alert.resolution || alert.acknowledged_by) && !compact && (
          <p className="text-xs text-muted-foreground">
            {resolved
              ? `${alert.resolution}${alert.resolved_at ? ` · ${timeAgo(alert.resolved_at)}` : ""}`
              : `Acknowledged by ${alert.acknowledged_by}${alert.acknowledged_at ? ` · ${timeAgo(alert.acknowledged_at)}` : ""}`}
          </p>
        )}
      </div>

      {canAct && !resolved && !compact && (
        <div className="flex shrink-0 flex-col gap-1.5 sm:flex-row sm:items-start">
          {alert.status === "open" && (
            <Button
              size="sm"
              variant="outline"
              disabled={action.isPending}
              onClick={() =>
                action.mutate(
                  { type: "acknowledge", id: alert.id },
                  { onError: (e) => toast.error(e.message) },
                )
              }
            >
              Acknowledge
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => setResolving(true)}>
            Resolve
          </Button>
        </div>
      )}

      <ResolveDialog alert={resolving ? alert : null} onClose={() => setResolving(false)} />
    </li>
  );
}

function ResolveDialog({ alert, onClose }: { alert: Alert | null; onClose: () => void }) {
  const action = useAlertAction();
  const [note, setNote] = useState("");
  return (
    <Dialog open={!!alert} onOpenChange={(open) => !open && !action.isPending && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Resolve alert</DialogTitle>
          <DialogDescription>{alert?.title}</DialogDescription>
        </DialogHeader>
        <form
          id="resolve-alert"
          className="space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!alert) return;
            action.mutate(
              { type: "resolve", id: alert.id, note: note.trim() || null },
              {
                onSuccess: () => {
                  toast.success("Alert resolved");
                  setNote("");
                  onClose();
                },
                onError: (err) => toast.error(err.message),
              },
            );
          }}
        >
          <Label htmlFor="resolve-note">What was done (optional)</Label>
          <Textarea
            id="resolve-note"
            value={note}
            maxLength={200}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. Telnet disabled on the lab PC, checked with the lab assistant"
          />
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={action.isPending}>
            Cancel
          </Button>
          <Button type="submit" form="resolve-alert" disabled={action.isPending}>
            {action.isPending && <Loader2 className="animate-spin" />}
            Resolve
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
