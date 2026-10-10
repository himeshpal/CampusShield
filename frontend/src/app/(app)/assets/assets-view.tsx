"use client";

import { AlertTriangle, Plus, Search } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useDeferredValue, useState } from "react";

import {
  AssetStatusBadge,
  AssetTypeLabel,
  CriticalityBadge,
} from "@/components/assets/asset-badges";
import { AssetFormDialog } from "@/components/assets/asset-form-dialog";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAssets, useAssetSummary } from "@/hooks/use-assets";
import { useCurrentUser } from "@/hooks/use-current-user";
import { ASSET_TYPES, displayName } from "@/lib/assets";
import { timeAgo } from "@/lib/format";
import type { Asset, AssetStatus, AssetType } from "@/lib/types";
import { cn } from "@/lib/utils";

const TABS: { value: AssetStatus | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "registered", label: "Registered" },
  { value: "unregistered", label: "Unregistered" },
  { value: "retired", label: "Retired" },
];

export function AssetsView() {
  const params = useSearchParams();
  const router = useRouter();
  const { user } = useCurrentUser();
  const isAdmin = user?.role === "admin";

  const initial = params.get("status") as AssetStatus | null;
  const [status, setStatus] = useState<AssetStatus | "all">(initial ?? "all");
  const [type, setType] = useState<AssetType | "all">("all");
  const [search, setSearch] = useState("");
  const q = useDeferredValue(search);

  const { data: summary } = useAssetSummary();
  const { data: assets, isLoading } = useAssets({
    status: status === "all" ? undefined : status,
    asset_type: type === "all" ? undefined : type,
    q: q || undefined,
  });

  const [dialog, setDialog] = useState<{ mode: "create" | "edit" | "register"; asset?: Asset } | null>(null);

  const counts: Record<string, number | undefined> = {
    all: summary && summary.registered + summary.unregistered + summary.retired,
    registered: summary?.registered,
    unregistered: summary?.unregistered,
    retired: summary?.retired,
  };

  return (
    <>
      <PageHeader
        title="Assets"
        description="Persistent inventory of every campus IT device, kept current by each scan."
        actions={
          isAdmin && (
            <Button onClick={() => setDialog({ mode: "create" })}>
              <Plus />
              Add asset
            </Button>
          )
        }
      />

      {!!summary?.unregistered && status !== "unregistered" && (
        <div className="mb-4 flex flex-col gap-3 rounded-xl border border-risk-high/40 bg-risk-high/5 p-4 sm:flex-row sm:items-center">
          <AlertTriangle className="size-5 shrink-0 text-risk-high" />
          <p className="flex-1 text-sm">
            <span className="font-medium">
              {summary.unregistered} unregistered {summary.unregistered === 1 ? "device" : "devices"}
            </span>{" "}
            seen on the network. Identify and register {summary.unregistered === 1 ? "it" : "them"},
            or investigate as a possible rogue device.
          </p>
          <Button variant="outline" size="sm" onClick={() => setStatus("unregistered")}>
            Review
          </Button>
        </div>
      )}

      <Card className="py-0">
        <CardContent className="space-y-4 p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap gap-1 rounded-lg bg-muted p-1" role="tablist">
              {TABS.map((tab) => (
                <button
                  key={tab.value}
                  role="tab"
                  aria-selected={status === tab.value}
                  onClick={() => setStatus(tab.value)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1 text-sm font-medium text-muted-foreground transition-colors",
                    status === tab.value && "bg-background text-foreground shadow-sm",
                  )}
                >
                  {tab.label}
                  {counts[tab.value] !== undefined && (
                    <span
                      className={cn(
                        "rounded-full px-1.5 text-xs tabular-nums",
                        tab.value === "unregistered" && counts[tab.value]
                          ? "bg-risk-high/15 text-risk-high"
                          : "bg-background/60",
                      )}
                    >
                      {counts[tab.value]}
                    </span>
                  )}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <div className="relative flex-1 lg:w-72">
                <Search className="absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search tag, name, IP, MAC, owner…"
                  className="pl-8"
                  aria-label="Search assets"
                />
              </div>
              <Select value={type} onValueChange={(v) => setType(v as AssetType | "all")}>
                <SelectTrigger className="w-44" aria-label="Filter by type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  {ASSET_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      <t.icon />
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Asset</TableHead>
                <TableHead>Network</TableHead>
                <TableHead>Department</TableHead>
                <TableHead>Criticality</TableHead>
                <TableHead>Open ports</TableHead>
                <TableHead>Status</TableHead>
                {isAdmin && <TableHead className="w-24" />}
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading &&
                Array.from({ length: 5 }, (_, i) => (
                  <TableRow key={i}>
                    <TableCell colSpan={7}>
                      <Skeleton className="h-8 w-full" />
                    </TableCell>
                  </TableRow>
                ))}
              {assets?.map((asset) => (
                <AssetRow
                  key={asset.id}
                  asset={asset}
                  isAdmin={isAdmin}
                  onOpen={() => router.push(`/assets/${asset.id}`)}
                  onAction={(mode) => setDialog({ mode, asset })}
                />
              ))}
              {assets?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="py-12 text-center text-muted-foreground">
                    No assets match these filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {dialog && (
        <AssetFormDialog
          mode={dialog.mode}
          asset={dialog.asset}
          open
          onOpenChange={(open) => !open && setDialog(null)}
        />
      )}
    </>
  );
}

function AssetRow({
  asset,
  isAdmin,
  onOpen,
  onAction,
}: {
  asset: Asset;
  isAdmin: boolean;
  onOpen: () => void;
  onAction: (mode: "edit" | "register") => void;
}) {
  const baseline = new Set(asset.baseline_ports);
  const unregistered = asset.status === "unregistered";

  return (
    <TableRow
      onClick={onOpen}
      className={cn(
        "cursor-pointer",
        unregistered && "bg-risk-high/5 hover:bg-risk-high/10",
        asset.status === "retired" && "opacity-60",
      )}
    >
      <TableCell>
        <div className="grid gap-0.5">
          <Link
            href={`/assets/${asset.id}`}
            className="font-medium hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {unregistered && !asset.name ? (
              <span className="text-risk-high">Unknown device</span>
            ) : (
              displayName(asset)
            )}
          </Link>
          <span className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="font-mono">{asset.asset_tag}</span>
            <AssetTypeLabel type={asset.asset_type} />
          </span>
        </div>
      </TableCell>
      <TableCell>
        <div className="grid min-w-36 gap-0.5 font-mono text-xs">
          <span>{asset.ip_address ?? "—"}</span>
          <span className="max-w-40 truncate text-muted-foreground" title={asset.mac_vendor ?? undefined}>
            {asset.mac_vendor ?? asset.mac_address ?? ""}
          </span>
        </div>
      </TableCell>
      <TableCell>
        <div className="grid min-w-32 max-w-48 gap-0.5 text-sm whitespace-normal">
          <span>{asset.department ?? "—"}</span>
          <span className="text-xs text-muted-foreground">{asset.location}</span>
        </div>
      </TableCell>
      <TableCell>
        <CriticalityBadge level={asset.criticality_level} total={asset.criticality} />
      </TableCell>
      <TableCell>
        <div className="flex max-w-36 flex-wrap gap-1">
          {asset.observed_ports === null && <span className="text-xs text-muted-foreground">Not scanned</span>}
          {asset.observed_ports?.map((p) => {
            const unexpected = !unregistered && !baseline.has(p.port);
            return (
              <Badge
                key={p.port}
                variant={unexpected ? "outline" : "secondary"}
                className={cn(
                  "font-mono font-normal",
                  unexpected && "border-risk-high/50 bg-risk-high/10 text-risk-high",
                )}
                title={unexpected ? "Not in the expected baseline" : p.service ?? undefined}
              >
                {p.port}
              </Badge>
            );
          })}
        </div>
      </TableCell>
      <TableCell>
        <div className="grid justify-items-start gap-1">
          <AssetStatusBadge status={asset.status} />
          <span className="text-xs text-muted-foreground">
            {asset.last_seen_at ? `Seen ${timeAgo(asset.last_seen_at)}` : "Never seen"}
          </span>
        </div>
      </TableCell>
      {isAdmin && (
        <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
          {unregistered ? (
            <Button size="sm" onClick={() => onAction("register")}>
              Register
            </Button>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => onAction("edit")}>
              Edit
            </Button>
          )}
        </TableCell>
      )}
    </TableRow>
  );
}
