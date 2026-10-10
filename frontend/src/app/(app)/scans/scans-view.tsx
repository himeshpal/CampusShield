"use client";

import { Radar } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/page-header";
import { ActiveScanCard } from "@/components/scans/active-scan-card";
import { NewScanDialog } from "@/components/scans/new-scan-dialog";
import { PROFILE_LABELS, ScanStatusBadge } from "@/components/scans/scan-status-badge";
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
import { useCurrentUser } from "@/hooks/use-current-user";
import { useActiveScan, useScanHistory } from "@/hooks/use-scans";
import { duration, timeAgo } from "@/lib/format";

export function ScansView() {
  const { user } = useCurrentUser();
  const isAdmin = user?.role === "admin";
  const { data: active } = useActiveScan();
  const { data: history, isLoading } = useScanHistory();
  const router = useRouter();

  return (
    <>
      <PageHeader
        title="Network scans"
        description="Discover live hosts, open ports and running services on authorised subnets."
        actions={isAdmin && <NewScanDialog disabled={!!active} />}
      />

      {active && (
        <div className="mb-6">
          <ActiveScanCard scan={active} canCancel={isAdmin} />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Scan history</CardTitle>
          <CardDescription>Every scan is kept, so results can be compared over time.</CardDescription>
        </CardHeader>
        <CardContent>
          {!isLoading && history?.length === 0 ? (
            <div className="flex flex-col items-center gap-3 py-12 text-center">
              <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Radar className="size-6" />
              </div>
              <div>
                <p className="font-medium">No scans yet</p>
                <p className="text-sm text-muted-foreground">
                  {isAdmin
                    ? "Run the first scan to discover what is on the campus network."
                    : "An administrator has not run any scans yet."}
                </p>
              </div>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">Scan</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Profile</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Hosts</TableHead>
                  <TableHead className="text-right">Open ports</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>By</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading &&
                  Array.from({ length: 3 }, (_, i) => (
                    <TableRow key={i}>
                      <TableCell colSpan={9}>
                        <Skeleton className="h-5 w-full" />
                      </TableCell>
                    </TableRow>
                  ))}
                {history?.map((scan) => (
                  <TableRow
                    key={scan.id}
                    className="cursor-pointer"
                    onClick={() => router.push(`/scans/${scan.id}`)}
                  >
                    <TableCell className="font-medium">
                      {/* real link: works before hydration, keyboard and new-tab friendly */}
                      <Link
                        href={`/scans/${scan.id}`}
                        className="hover:underline"
                        onClick={(e) => e.stopPropagation()}
                      >
                        #{scan.id}
                      </Link>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{scan.target}</TableCell>
                    <TableCell>{PROFILE_LABELS[scan.profile]}</TableCell>
                    <TableCell>
                      <ScanStatusBadge status={scan.status} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {scan.status === "completed" ? scan.hosts_up : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {scan.status === "completed" ? scan.open_ports : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {timeAgo(scan.created_at)}
                    </TableCell>
                    <TableCell className="tabular-nums text-muted-foreground">
                      {scan.finished_at ? duration(scan.started_at, scan.finished_at) : "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {scan.requested_by_name ?? scan.triggered_by}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
