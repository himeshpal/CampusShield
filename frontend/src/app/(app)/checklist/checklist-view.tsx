"use client";

import { AlertTriangle, Info } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ChecklistCell } from "@/components/checklist/checklist-cell";
import { PageHeader } from "@/components/page-header";
import { RiskBadge } from "@/components/risk/risk-badge";
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
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAssetSummary } from "@/hooks/use-assets";
import { useChecklist, useChecklistSummary } from "@/hooks/use-checklist";
import { useCurrentUser } from "@/hooks/use-current-user";
import { assetType, displayName } from "@/lib/assets";
import { CONTROL_STATUS, SHORT_LABELS, STATUS_ORDER } from "@/lib/checklist";
import type { ChecklistSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ChecklistView() {
  const { user } = useCurrentUser();
  const canEdit = user?.role === "admin";
  const { data: matrix, isLoading } = useChecklist();
  const { data: summary } = useChecklistSummary();
  const { data: inventory } = useAssetSummary();
  const [onlyIncomplete, setOnlyIncomplete] = useState(false);

  const rows = [...(matrix?.rows ?? [])]
    .sort((a, b) => (b.risk_score ?? -1) - (a.risk_score ?? -1))
    .filter((r) => !onlyIncomplete || r.answered < (matrix?.items.length ?? 0));

  return (
    <>
      <PageHeader
        title="Security checklist"
        description="Controls a network scan cannot see. Every answer feeds the asset's risk score."
      />

      {!!inventory?.unregistered && (
        <div className="mb-4 flex items-center gap-3 rounded-xl border border-risk-high/40 bg-risk-high/5 p-3 text-sm">
          <AlertTriangle className="size-4 shrink-0 text-risk-high-ink" />
          <p className="flex-1">
            {inventory.unregistered} unregistered{" "}
            {inventory.unregistered === 1 ? "device is" : "devices are"} not listed: a device
            needs an owner before its controls can be assessed.
          </p>
          <Link href="/assets?status=unregistered" className="font-medium text-primary hover:underline">
            Review
          </Link>
        </div>
      )}

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <ProgressTile summary={summary} />
        <CountTile
          label="Known gaps"
          value={summary?.gaps}
          hint="Controls answered “missing”"
          alarming={!!summary?.gaps}
        />
        <CountTile
          label="Not confirmed"
          value={summary && summary.total - summary.answered}
          hint="Nobody has checked yet"
        />
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Coverage by control</CardTitle>
          <CardDescription>Across all registered assets.</CardDescription>
        </CardHeader>
        <CardContent>{summary ? <Coverage summary={summary} /> : <Skeleton className="h-40 w-full" />}</CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div className="space-y-1.5">
            <CardTitle>Assets and controls</CardTitle>
            <CardDescription>
              {canEdit
                ? "Click a cell to record what you verified. Riskiest assets first."
                : "Riskiest assets first. Click a cell to see the evidence."}
            </CardDescription>
          </div>
          <label className="flex shrink-0 cursor-pointer items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={onlyIncomplete}
              onChange={(e) => setOnlyIncomplete(e.target.checked)}
              className="size-4 accent-[var(--primary)]"
            />
            Only incomplete
          </label>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-48">Asset</TableHead>
                {matrix?.items.map((item) => (
                  <TableHead key={item.key} className="w-24 text-center">
                    <Tooltip>
                      <TooltipTrigger className="inline-flex items-center gap-1 underline decoration-dotted underline-offset-4">
                        {SHORT_LABELS[item.key] ?? item.label}
                      </TooltipTrigger>
                      <TooltipContent className="max-w-64">
                        <p className="font-medium">{item.label}</p>
                        <p className="opacity-80">{item.description}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TableHead>
                ))}
                <TableHead className="text-right">Done</TableHead>
                <TableHead>Risk</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading &&
                Array.from({ length: 4 }, (_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={9}>
                      <Skeleton className="h-7 w-full" />
                    </TableCell>
                  </TableRow>
                ))}
              {rows.map((row) => {
                const label = displayName({ name: row.name, hostname: null, ip_address: row.asset_tag });
                const TypeIcon = assetType(row.asset_type).icon;
                return (
                  <TableRow key={row.asset_id}>
                    <TableCell>
                      <Link href={`/assets/${row.asset_id}`} className="group grid gap-0.5">
                        <span className="font-medium group-hover:underline">{label}</span>
                        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <TypeIcon className="size-3" />
                          <span className="font-mono">{row.asset_tag}</span>
                        </span>
                      </Link>
                    </TableCell>
                    {matrix!.items.map((item) => (
                      <TableCell key={item.key} className="px-1.5">
                        <ChecklistCell
                          assetId={row.asset_id}
                          assetLabel={label}
                          item={item}
                          entry={row.entries[item.key]!}
                          canEdit={canEdit}
                        />
                      </TableCell>
                    ))}
                    <TableCell className="text-right text-sm tabular-nums text-muted-foreground">
                      {row.answered}/{matrix!.items.length}
                    </TableCell>
                    <TableCell>
                      <RiskBadge score={row.risk_score} band={row.risk_band} />
                    </TableCell>
                  </TableRow>
                );
              })}
              {matrix && rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} className="py-10 text-center text-muted-foreground">
                    {onlyIncomplete ? "Every asset is fully assessed." : "No registered assets yet."}
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
          <p className="mt-4 flex items-start gap-2 text-xs text-muted-foreground">
            <Info className="mt-0.5 size-3.5 shrink-0" />
            “Missing” and “Not confirmed” each add 4 points to the asset&apos;s raw risk; “In place” and
            “Not applicable” add none.
          </p>
        </CardContent>
      </Card>
    </>
  );
}

function ProgressTile({ summary }: { summary?: ChecklistSummary }) {
  const pct = summary && summary.total ? Math.round((summary.answered / summary.total) * 100) : 0;
  return (
    <Card className="gap-3">
      <CardHeader>
        <CardDescription className="font-medium">Assessment progress</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-3xl font-semibold tracking-tight">
          {summary ? `${pct}%` : "—"}
        </p>
        <div
          className="h-1.5 overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-label="Assessment progress"
          aria-valuenow={pct}
        >
          <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
        </div>
        <p className="text-xs text-muted-foreground">
          {summary ? `${summary.answered} of ${summary.total} answers recorded` : " "}
        </p>
      </CardContent>
    </Card>
  );
}

function CountTile({
  label,
  value,
  hint,
  alarming,
}: {
  label: string;
  value?: number;
  hint: string;
  alarming?: boolean;
}) {
  return (
    <Card className={cn("gap-3", alarming && "border-risk-critical/40 bg-risk-critical/5")}>
      <CardHeader>
        <CardDescription className="font-medium">{label}</CardDescription>
      </CardHeader>
      <CardContent>
        <p className={cn("text-3xl font-semibold tracking-tight tabular-nums", alarming && "text-risk-critical-ink")}>
          {value ?? "—"}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
      </CardContent>
    </Card>
  );
}

/** One 100% stacked bar per control (2px gaps), with a shared legend. */
function Coverage({ summary }: { summary: ChecklistSummary }) {
  return (
    <div className="space-y-4">
      <ul className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
        {STATUS_ORDER.map((s) => {
          const Icon = CONTROL_STATUS[s].icon;
          return (
            <li key={s} className="flex items-center gap-1.5">
              <span className={cn("size-2.5 rounded-sm", CONTROL_STATUS[s].mark)} aria-hidden />
              <Icon className="size-3" aria-hidden />
              {CONTROL_STATUS[s].label}
            </li>
          );
        })}
      </ul>
      <div className="space-y-3">
        {summary.coverage.map((c) => {
          const total = STATUS_ORDER.reduce((n, s) => n + c.counts[s], 0) || 1;
          const shown = STATUS_ORDER.filter((s) => c.counts[s] > 0);
          return (
            <div key={c.key} className="grid items-center gap-x-4 gap-y-1 sm:grid-cols-[12rem_1fr_6rem]">
              <span className="text-sm">{c.label}</span>
              <div className="flex h-3 gap-0.5" role="img" aria-label={`${c.label}: ${STATUS_ORDER.map((s) => `${c.counts[s]} ${CONTROL_STATUS[s].label}`).join(", ")}`}>
                {shown.map((s, i) => (
                  <Tooltip key={s}>
                    <TooltipTrigger asChild>
                      <div
                        className={cn(
                          "h-full min-w-1.5",
                          CONTROL_STATUS[s].mark,
                          i === 0 && "rounded-l-sm",
                          i === shown.length - 1 && "rounded-r-sm",
                        )}
                        style={{ width: `${(c.counts[s] / total) * 100}%` }}
                      />
                    </TooltipTrigger>
                    <TooltipContent>
                      {CONTROL_STATUS[s].label}: {c.counts[s]} of {total}
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
              <span className="text-xs text-muted-foreground tabular-nums sm:text-right">
                {c.counts.yes + c.counts.na} of {total} covered
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
