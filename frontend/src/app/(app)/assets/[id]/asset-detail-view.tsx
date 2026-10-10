"use client";

import { AlertTriangle, ArrowLeft, Archive, Pencil, RotateCcw, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import {
  AssetStatusBadge,
  AssetTypeLabel,
  CriticalityBadge,
  MatchBadge,
} from "@/components/assets/asset-badges";
import { AssetFormDialog } from "@/components/assets/asset-form-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { useAsset, useSaveAsset } from "@/hooks/use-assets";
import { useCurrentUser } from "@/hooks/use-current-user";
import { ApiError } from "@/lib/api";
import { CRITERIA, displayName, LEVELS } from "@/lib/assets";
import { dateTime, softwareLabel, timeAgo } from "@/lib/format";
import type { AssetDetail } from "@/lib/types";
import { cn } from "@/lib/utils";

export function AssetDetailView() {
  const { id } = useParams<{ id: string }>();
  const { data: asset, error } = useAsset(Number(id));
  const { user } = useCurrentUser();
  const isAdmin = user?.role === "admin";
  const [dialog, setDialog] = useState<"edit" | "register" | null>(null);
  const save = useSaveAsset();

  if (error instanceof ApiError && error.status === 404) {
    return (
      <div className="py-16 text-center">
        <p className="font-medium">This asset does not exist.</p>
        <Button asChild variant="link">
          <Link href="/assets">Back to assets</Link>
        </Button>
      </div>
    );
  }
  if (!asset) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  const unregistered = asset.status === "unregistered";
  function setStatus(status: "retired" | "registered") {
    save.mutate(
      { mode: "edit", id: asset!.id, fields: { status } },
      {
        onSuccess: () => toast.success(status === "retired" ? "Asset retired" : "Asset reactivated"),
        onError: (e) => toast.error(e.message),
      },
    );
  }

  return (
    <>
      <Link
        href="/assets"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Assets
      </Link>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">
              {unregistered && !asset.name ? "Unknown device" : displayName(asset)}
            </h1>
            <AssetStatusBadge status={asset.status} />
          </div>
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
            <span className="font-mono">{asset.asset_tag}</span>
            <AssetTypeLabel type={asset.asset_type} />
            {asset.last_seen_at && <span>Last seen {timeAgo(asset.last_seen_at)}</span>}
          </p>
        </div>
        {isAdmin && (
          <div className="flex gap-2">
            {unregistered ? (
              <Button onClick={() => setDialog("register")}>
                <ShieldCheck />
                Register device
              </Button>
            ) : (
              <Button variant="outline" onClick={() => setDialog("edit")}>
                <Pencil />
                Edit
              </Button>
            )}
            {asset.status === "registered" && (
              <Button variant="outline" onClick={() => setStatus("retired")} disabled={save.isPending}>
                <Archive />
                Retire
              </Button>
            )}
            {asset.status === "retired" && (
              <Button variant="outline" onClick={() => setStatus("registered")} disabled={save.isPending}>
                <RotateCcw />
                Reactivate
              </Button>
            )}
          </div>
        )}
      </div>

      {unregistered && (
        <div className="mb-6 flex gap-3 rounded-xl border border-risk-high/40 bg-risk-high/5 p-4 text-sm">
          <AlertTriangle className="size-5 shrink-0 text-risk-high" />
          <div>
            <p className="font-medium">Not in the inventory</p>
            <p className="text-muted-foreground">
              Discovered automatically {asset.first_seen_at && `on ${dateTime(asset.first_seen_at)}`}{" "}
              and seen in {asset.observations.length}{" "}
              {asset.observations.length === 1 ? "scan" : "scans"} since. Nobody has registered it,
              so it has no owner, location or approved services. Register it if it belongs on the
              network; otherwise locate and remove it.
            </p>
          </div>
        </div>
      )}

      {/* min-w-0: grid items default to min-width:auto, so a wide table would push the
          column past the screen edge on phones instead of scrolling inside its card */}
      <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
        <div className="min-w-0 space-y-6">
          <ExposureCard asset={asset} />
          <HistoryCard asset={asset} />
        </div>
        <div className="min-w-0 space-y-6">
          <DetailsCard asset={asset} />
          <CriticalityCard asset={asset} />
        </div>
      </div>

      {dialog && (
        <AssetFormDialog mode={dialog} asset={asset} open onOpenChange={(o) => !o && setDialog(null)} />
      )}
    </>
  );
}

function ExposureCard({ asset }: { asset: AssetDetail }) {
  const baseline = new Set(asset.baseline_ports);
  const observed = asset.observed_ports ?? [];
  const observedSet = new Set(observed.map((p) => p.port));
  const missing = asset.baseline_ports.filter((p) => !observedSet.has(p));
  const unexpected = observed.filter((p) => !baseline.has(p.port));
  const unregistered = asset.status === "unregistered";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Network exposure</CardTitle>
        <CardDescription>
          {asset.observed_ports === null
            ? "Not seen by any scan yet."
            : unregistered
              ? `Open ports from scan #${asset.last_scan_id}. No baseline: the device is not registered.`
              : unexpected.length
                ? `${unexpected.length} port${unexpected.length > 1 ? "s" : ""} open that ${
                    unexpected.length > 1 ? "are" : "is"
                  } not in the expected baseline (scan #${asset.last_scan_id}).`
                : `Matches the expected baseline (scan #${asset.last_scan_id}).`}
        </CardDescription>
      </CardHeader>
      {observed.length > 0 && (
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">Port</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Software</TableHead>
                {!unregistered && <TableHead className="text-right">Baseline</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {observed.map((p) => {
                const expected = baseline.has(p.port);
                return (
                  <TableRow key={p.port} className={cn(!unregistered && !expected && "bg-risk-high/5")}>
                    <TableCell className="font-mono">
                      {p.port}/{p.protocol}
                    </TableCell>
                    <TableCell>{p.service ?? "—"}</TableCell>
                    <TableCell className="font-medium">
                      {softwareLabel(p.product, p.version) ?? (
                        <span className="font-normal text-muted-foreground">Not identified</span>
                      )}
                    </TableCell>
                    {!unregistered && (
                      <TableCell className="text-right">
                        {expected ? (
                          <Badge variant="outline" className="font-normal text-muted-foreground">
                            Expected
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="border-risk-high/50 bg-risk-high/10 font-normal text-risk-high">
                            Unexpected
                          </Badge>
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          {!unregistered && missing.length > 0 && (
            <p className="mt-3 text-xs text-muted-foreground">
              Expected but not seen: {missing.map((p) => <span key={p} className="font-mono">{p} </span>)}
            </p>
          )}
        </CardContent>
      )}
    </Card>
  );
}

function HistoryCard({ asset }: { asset: AssetDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Scan history</CardTitle>
        <CardDescription>Every scan that saw this device, newest first.</CardDescription>
      </CardHeader>
      <CardContent>
        {asset.observations.length === 0 ? (
          <p className="text-sm text-muted-foreground">No observations yet.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">Scan</TableHead>
                <TableHead>When</TableHead>
                <TableHead>IP address</TableHead>
                <TableHead>Matched</TableHead>
                <TableHead>Open ports</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {asset.observations.map((o) => (
                <TableRow key={o.scan_id}>
                  <TableCell>
                    <Link href={`/scans/${o.scan_id}`} className="font-medium hover:underline">
                      #{o.scan_id}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{dateTime(o.scanned_at)}</TableCell>
                  <TableCell className="font-mono text-xs">{o.ip_address}</TableCell>
                  <TableCell>{o.match_method && <MatchBadge method={o.match_method} />}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {o.ports.map((p) => p.port).join(", ") || "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}

function DetailsCard({ asset }: { asset: AssetDetail }) {
  const rows: [string, React.ReactNode][] = [
    ["IP address", asset.ip_address && <span className="font-mono">{asset.ip_address}</span>],
    ["MAC address", asset.mac_address && <span className="font-mono">{asset.mac_address}</span>],
    ["Vendor", asset.mac_vendor],
    ["Hostname", asset.hostname],
    ["Operating system", asset.os_name],
    ["Department", asset.department],
    ["Location", asset.location],
    ["Owner", asset.owner],
    ["First seen", asset.first_seen_at && dateTime(asset.first_seen_at)],
    ["Added to inventory", dateTime(asset.created_at)],
  ];
  return (
    <Card>
      <CardHeader>
        <CardTitle>Details</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="divide-y text-sm">
          {rows.map(([label, value]) => (
            <div key={label} className="flex justify-between gap-4 py-2">
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="text-right">{value || <span className="text-muted-foreground">—</span>}</dd>
            </div>
          ))}
        </dl>
        {asset.notes && <p className="mt-3 rounded-md bg-muted/60 p-3 text-sm">{asset.notes}</p>}
      </CardContent>
    </Card>
  );
}

function CriticalityCard({ asset }: { asset: AssetDetail }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between">
        <div className="space-y-1.5">
          <CardTitle>Criticality</CardTitle>
          <CardDescription>How much the campus depends on it.</CardDescription>
        </div>
        <CriticalityBadge level={asset.criticality_level} total={asset.criticality} />
      </CardHeader>
      <CardContent className="space-y-3">
        {CRITERIA.map((c) => {
          const value = asset[c.key];
          return (
            <div key={c.key} className="space-y-1">
              <div className="flex justify-between text-sm">
                <span>{c.label}</span>
                <span className="text-muted-foreground">{LEVELS[value - 1]}</span>
              </div>
              <div className="flex gap-1">
                {[1, 2, 3].map((step) => (
                  <div
                    key={step}
                    className={cn("h-1.5 flex-1 rounded-full", step <= value ? "bg-primary" : "bg-muted")}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
