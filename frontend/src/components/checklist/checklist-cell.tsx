"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Textarea } from "@/components/ui/textarea";
import { useSaveControl } from "@/hooks/use-checklist";
import { CONTROL_STATUS, STATUS_ORDER } from "@/lib/checklist";
import { timeAgo } from "@/lib/format";
import { BANDS, formatScore } from "@/lib/risk";
import type { ChecklistEntry, ChecklistItem, ChecklistSaveResult, ControlStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

function announce(assetLabel: string, result: ChecklistSaveResult) {
  const { before, after, band_after } = result.risk;
  if (before === null || after === null || band_after === null) return toast.success("Saved");
  const delta = Math.round(after) - Math.round(before);
  const change = delta === 0 ? "unchanged" : `${formatScore(before)} → ${formatScore(after)}`;
  const message = `${assetLabel}: risk ${change}`;
  const description = `${BANDS[band_after].label} risk${delta < 0 ? ` (${delta} points)` : ""}`;
  return delta < 0 ? toast.success(message, { description }) : toast(message, { description });
}

/** One control for one asset: a compact cell that opens an editor. */
export function ChecklistCell({
  assetId,
  assetLabel,
  item,
  entry,
  canEdit,
  variant = "cell",
}: {
  assetId: number;
  assetLabel: string;
  item: ChecklistItem;
  entry: ChecklistEntry;
  canEdit: boolean;
  variant?: "cell" | "row";
}) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<ControlStatus>(entry.status);
  const [evidence, setEvidence] = useState(entry.evidence ?? "");
  const save = useSaveControl();
  const meta = CONTROL_STATUS[entry.status];
  const Icon = meta.icon;

  function onOpenChange(next: boolean) {
    if (next) {
      // start from what is saved each time the editor opens
      setStatus(entry.status);
      setEvidence(entry.evidence ?? "");
    }
    setOpen(next);
  }

  function submit() {
    save.mutate(
      { assetId, key: item.key, status, evidence: evidence.trim() || null },
      {
        onSuccess: (result) => {
          announce(assetLabel, result);
          setOpen(false);
        },
        onError: (e) => toast.error(e.message),
      },
    );
  }

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`${item.label} for ${assetLabel}: ${meta.label}`}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border text-xs font-medium transition-colors hover:brightness-95 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
            meta.cell,
            variant === "cell" ? "h-7 w-full justify-center px-2" : "h-7 px-2.5",
          )}
        >
          <Icon className="size-3.5" />
          {variant === "cell" ? meta.short : meta.label}
          {entry.evidence && <span className="size-1 rounded-full bg-current opacity-60" title="Has evidence note" />}
        </button>
      </PopoverTrigger>
      {/* Never taller than the space Radix measured: on a short laptop screen the Save
          button would otherwise end up off-screen, and a fixed popover cannot be scrolled
          into view by scrolling the page. */}
      <PopoverContent
        className="max-h-(--radix-popover-content-available-height) w-80 space-y-3 overflow-y-auto"
        align="center"
        collisionPadding={12}
      >
        <div>
          <p className="text-sm font-medium">{item.label}</p>
          <p className="text-xs text-muted-foreground">{item.description}</p>
          <p className="mt-1 text-xs text-muted-foreground">{assetLabel}</p>
        </div>

        <div role="radiogroup" aria-label="Status" className="grid grid-cols-2 gap-1.5">
          {STATUS_ORDER.map((s) => {
            const m = CONTROL_STATUS[s];
            const SIcon = m.icon;
            return (
              <button
                key={s}
                type="button"
                role="radio"
                aria-checked={status === s}
                disabled={!canEdit}
                onClick={() => setStatus(s)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md border px-2 py-1.5 text-xs font-medium transition-colors disabled:cursor-default",
                  status === s ? m.cell : "border-border text-muted-foreground hover:bg-muted",
                  status === s && "ring-2 ring-ring/40",
                )}
              >
                <SIcon className="size-3.5" />
                {m.label}
              </button>
            );
          })}
        </div>
        <p className="text-xs leading-snug text-muted-foreground">{CONTROL_STATUS[status].hint}</p>

        <div className="space-y-1.5">
          <Label htmlFor={`evidence-${assetId}-${item.key}`} className="text-xs">
            Evidence note
          </Label>
          <Textarea
            id={`evidence-${assetId}-${item.key}`}
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
            maxLength={500}
            rows={2}
            readOnly={!canEdit}
            placeholder={canEdit ? "e.g. BitLocker status checked on 10 Oct" : "No note"}
            className="text-xs"
          />
        </div>

        {entry.updated_by && entry.updated_at && (
          <p className="text-xs text-muted-foreground">
            Last set by {entry.updated_by}, {timeAgo(entry.updated_at)}
          </p>
        )}

        {canEdit && (
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={submit} disabled={save.isPending}>
              {save.isPending && <Loader2 className="animate-spin" />}
              Save
            </Button>
          </div>
        )}
      </PopoverContent>
    </Popover>
  );
}
