"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2, Radar, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { useScanOptions } from "@/hooks/use-scans";
import { api } from "@/lib/api";
import type { Scan, ScanProfileKey } from "@/lib/types";
import { cn } from "@/lib/utils";

export function NewScanDialog({ disabled }: { disabled?: boolean }) {
  const [open, setOpen] = useState(false);
  const { data: options } = useScanOptions();
  const [target, setTarget] = useState<string | null>(null);
  const [profile, setProfile] = useState<ScanProfileKey>("standard");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const effectiveTarget = target ?? options?.default_target ?? "";
  const selected = options?.profiles.find((p) => p.key === profile);
  // preview with the target being typed
  const preview = selected?.command.replace(/\S+$/, effectiveTarget || "<target>");

  const start = useMutation({
    mutationFn: () =>
      api<Scan>("/scans", { method: "POST", json: { target: effectiveTarget, profile } }),
    onSuccess: (scan) => {
      queryClient.setQueryData(["scans", "active"], scan);
      queryClient.invalidateQueries({ queryKey: ["scans", "list"] });
      toast.success(`Scan #${scan.id} started`, { description: `${scan.target} · ${profile}` });
      setOpen(false);
    },
    onError: (e) => setError(e.message),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        setError(null);
      }}
    >
      <DialogTrigger asChild>
        <Button disabled={disabled}>
          <Radar />
          New scan
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>New network scan</DialogTitle>
          <DialogDescription>
            Discover live hosts, open ports and services with Nmap.
          </DialogDescription>
        </DialogHeader>

        <form
          id="new-scan"
          className="space-y-5"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            start.mutate();
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="target">Target</Label>
            <Input
              id="target"
              value={effectiveTarget}
              onChange={(e) => setTarget(e.target.value)}
              className="font-mono"
              placeholder="172.25.0.0/24"
              aria-invalid={!!error}
            />
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <ShieldCheck className="size-3.5 text-primary" />
              Authorised scope: {options?.authorized_subnets.join(", ") || "…"}
              {options?.excluded.length ? ` · never scanned: ${options.excluded.join(", ")}` : ""}
            </p>
          </div>

          <div className="space-y-2">
            <Label>Scan profile</Label>
            <RadioGroup
              value={profile}
              onValueChange={(v) => setProfile(v as ScanProfileKey)}
              className="gap-2"
            >
              {options?.profiles.map((p) => (
                <Label
                  key={p.key}
                  htmlFor={`profile-${p.key}`}
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-lg border p-3 font-normal transition-colors hover:bg-muted/50",
                    profile === p.key && "border-primary/50 bg-primary/5 hover:bg-primary/5",
                  )}
                >
                  <RadioGroupItem id={`profile-${p.key}`} value={p.key} className="mt-0.5" />
                  <div className="grid flex-1 gap-0.5">
                    <span className="flex items-center justify-between font-medium">
                      {p.label}
                      <span className="text-xs font-normal text-muted-foreground">
                        {p.estimate}
                      </span>
                    </span>
                    <span className="text-xs leading-relaxed text-muted-foreground">
                      {p.description}
                    </span>
                  </div>
                </Label>
              ))}
            </RadioGroup>
          </div>

          {preview && (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Command</p>
              <pre className="overflow-x-auto rounded-md bg-muted px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre-wrap break-all">
                {preview}
              </pre>
            </div>
          )}

          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
        </form>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button type="submit" form="new-scan" disabled={start.isPending || !effectiveTarget}>
            {start.isPending ? <Loader2 className="animate-spin" /> : <Radar />}
            Start scan
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
