"use client";

import { useMutation } from "@tanstack/react-query";
import { Loader2, Radar, Square } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import { duration } from "@/lib/format";
import type { Scan } from "@/lib/types";

import { PROFILE_LABELS } from "./scan-status-badge";

function useTicker(active: boolean) {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [active]);
}

export function ActiveScanCard({ scan, canCancel }: { scan: Scan; canCancel: boolean }) {
  useTicker(true); // keeps the elapsed time moving between polls

  const cancel = useMutation({
    mutationFn: () => api<Scan>(`/scans/${scan.id}/cancel`, { method: "POST" }),
    onSuccess: () => toast.info("Cancelling scan…"),
    onError: (e) => toast.error(e.message),
  });

  return (
    <Card className="overflow-hidden border-primary/30 py-0">
      <div className="h-1 w-full bg-primary/10">
        <div className="h-full w-1/3 animate-[scan_1.6s_ease-in-out_infinite] bg-primary/60" />
      </div>
      <CardContent className="flex flex-col gap-4 py-5 sm:flex-row sm:items-center">
        <div className="relative flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Radar className="size-5" />
          <span className="absolute -top-0.5 -right-0.5 size-2.5 animate-ping rounded-full bg-primary" />
        </div>

        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <Link href={`/scans/${scan.id}`} className="font-medium hover:underline">
              Scan #{scan.id} in progress
            </Link>
            <span className="font-mono text-sm text-muted-foreground">{scan.target}</span>
            <span className="text-sm text-muted-foreground">
              {PROFILE_LABELS[scan.profile]} profile
            </span>
          </div>
          <Progress value={scan.progress} className="h-2" aria-label="Scan progress" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Loader2 className="size-3 animate-spin" />
              {scan.phase ?? "Starting"}… {scan.progress}%
            </span>
            <span className="tabular-nums">{duration(scan.started_at ?? scan.created_at)}</span>
          </div>
        </div>

        {canCancel && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => cancel.mutate()}
            disabled={cancel.isPending}
          >
            <Square className="size-3 fill-current" />
            Cancel
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
