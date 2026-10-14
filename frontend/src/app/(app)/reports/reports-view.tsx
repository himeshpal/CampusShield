"use client";

import {
  AlertTriangle,
  Download,
  ExternalLink,
  FileText,
  Loader2,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/page-header";
import { GenerateReportDialog } from "@/components/reports/generate-report-dialog";
import { RiskBadge } from "@/components/risk/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { useCurrentUser } from "@/hooks/use-current-user";
import { reportPdfUrl, useDeleteReport, useReports } from "@/hooks/use-reports";
import { useScanHistory } from "@/hooks/use-scans";
import { dateTime, fileSize, timeAgo } from "@/lib/format";
import type { Report } from "@/lib/types";

const SECTIONS = [
  "Executive summary with key findings",
  "Priority recommendations",
  "Asset risk register",
  "Vulnerabilities and misconfigurations",
  "Unregistered devices",
  "Security checklist coverage",
  "Per-device evidence (full report)",
  "Scope, risk model and sign-off",
];

function PdfButtons({ report, compact }: { report: Report; compact?: boolean }) {
  return (
    <>
      <Button asChild variant={compact ? "ghost" : "outline"} size={compact ? "icon-sm" : "default"}>
        <a
          href={reportPdfUrl(report.id)}
          target="_blank"
          rel="noopener"
          aria-label={`Open ${report.number}`}
          title="Open in a new tab"
        >
          <ExternalLink />
          {!compact && "Open"}
        </a>
      </Button>
      <Button asChild variant={compact ? "ghost" : "default"} size={compact ? "icon-sm" : "default"}>
        <a
          href={reportPdfUrl(report.id, true)}
          aria-label={`Download ${report.number}`}
          title="Download PDF"
        >
          <Download />
          {!compact && "Download PDF"}
        </a>
      </Button>
    </>
  );
}

function Stat({ value, label }: { value: React.ReactNode; label: string }) {
  return (
    <div>
      <p className="text-xl font-semibold tabular-nums">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function LatestReport({ report, latestScanId }: { report: Report; latestScanId?: number }) {
  const s = report.summary;
  const stale = latestScanId != null && (s.latest_scan_id ?? 0) < latestScanId;
  const checklist = s.checklist_total
    ? `${Math.round((100 * s.checklist_answered) / s.checklist_total)}%`
    : "—";
  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1.5">
          <CardDescription className="font-mono text-xs">{report.number} · latest</CardDescription>
          <CardTitle className="text-lg">{report.title}</CardTitle>
          <CardDescription>
            {dateTime(report.created_at)} · {report.generated_by ?? "system"} · {report.pages} pages
            {s.latest_scan_id ? ` · data from scan #${s.latest_scan_id}` : ""}
          </CardDescription>
        </div>
        <div className="flex shrink-0 gap-2">
          <PdfButtons report={report} />
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 rounded-lg border bg-muted/20 p-4 sm:grid-cols-5">
          <div>
            <div className="h-7">
              <RiskBadge score={s.average} band={s.average_band} className="text-sm" />
            </div>
            <p className="mt-1 text-xs text-muted-foreground">average risk</p>
          </div>
          <Stat value={s.bands.high + s.bands.critical} label="high or critical" />
          <Stat value={s.vulnerabilities} label="vulnerabilities" />
          <Stat value={s.unregistered} label="unregistered devices" />
          <Stat value={checklist} label="checklist complete" />
        </div>
        {stale && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <AlertTriangle className="size-4 text-risk-high-ink" />
            Newer scan data exists (scan #{latestScanId}). Generate a new report for the current state.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function DeleteReportDialog({
  report,
  onClose,
}: {
  report: Report | null;
  onClose: () => void;
}) {
  const remove = useDeleteReport();
  return (
    <Dialog open={!!report} onOpenChange={(open) => !open && !remove.isPending && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Delete {report?.number}?</DialogTitle>
          <DialogDescription>
            “{report?.title}” will be removed from the history. Copies already downloaded are not
            affected. The deletion is recorded in the audit log.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={remove.isPending}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={remove.isPending}
            onClick={() =>
              report &&
              remove.mutate(report.id, {
                onSuccess: () => {
                  toast.success(`${report.number} deleted`);
                  onClose();
                },
                onError: (e) => toast.error(e.message),
              })
            }
          >
            {remove.isPending ? <Loader2 className="animate-spin" /> : <Trash2 />}
            Delete report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function ReportsView() {
  const { user } = useCurrentUser();
  const isAdmin = user?.role === "admin";
  const { data: reports, isLoading } = useReports();
  const { data: scans } = useScanHistory();
  const [deleting, setDeleting] = useState<Report | null>(null);
  const latestScanId = scans?.find((s) => s.status === "completed")?.id;
  const latest = reports?.[0];

  return (
    <>
      <PageHeader
        title="Reports"
        description="Point-in-time PDF audit reports for the institution, kept with their history."
        actions={<GenerateReportDialog />}
      />

      {isLoading && <Skeleton className="h-52 w-full rounded-xl" />}

      {!isLoading && !latest && (
        <Card>
          <CardContent className="grid gap-8 py-6 md:grid-cols-[1fr_1fr]">
            <div className="flex flex-col items-start gap-4">
              <div className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <FileText className="size-6" />
              </div>
              <div className="space-y-1.5">
                <h2 className="text-lg font-semibold">No reports yet</h2>
                <p className="text-sm text-muted-foreground">
                  Generate the first audit report: a PDF built from the latest scan results, risk
                  scores and checklist answers, ready to submit to the institution.
                </p>
              </div>
              <GenerateReportDialog />
            </div>
            <div>
              <p className="mb-2 text-sm font-medium">What the report contains</p>
              <ol className="space-y-1.5 text-sm text-muted-foreground">
                {SECTIONS.map((s, i) => (
                  <li key={s} className="flex gap-2">
                    <span className="w-4 text-right tabular-nums text-primary">{i + 1}</span>
                    {s}
                  </li>
                ))}
              </ol>
            </div>
          </CardContent>
        </Card>
      )}

      {latest && <LatestReport report={latest} latestScanId={latestScanId} />}

      {!!reports?.length && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Report history</CardTitle>
            <CardDescription>
              Every generated report is kept unchanged, so posture can be compared over time.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Report</TableHead>
                  <TableHead>Generated</TableHead>
                  <TableHead>Average risk</TableHead>
                  <TableHead className="text-right">High / critical</TableHead>
                  <TableHead className="text-right">Pages</TableHead>
                  <TableHead className="text-right">Size</TableHead>
                  <TableHead className="w-28 text-right">
                    <span className="sr-only">Actions</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell>
                      <p className="font-medium">{r.title}</p>
                      <p className="font-mono text-xs text-muted-foreground">
                        {r.number}
                        {r.include_details ? "" : " · summary only"}
                      </p>
                    </TableCell>
                    <TableCell>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="text-sm">{timeAgo(r.created_at)}</span>
                        </TooltipTrigger>
                        <TooltipContent>{dateTime(r.created_at)}</TooltipContent>
                      </Tooltip>
                      <p className="text-xs text-muted-foreground">{r.generated_by ?? "system"}</p>
                    </TableCell>
                    <TableCell>
                      <RiskBadge score={r.summary.average} band={r.summary.average_band} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {r.summary.bands.high + r.summary.bands.critical}
                      <span className="text-muted-foreground"> / {r.summary.assessed}</span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{r.pages}</TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {fileSize(r.size_bytes)}
                    </TableCell>
                    <TableCell>
                      <div className="flex justify-end gap-0.5">
                        <PdfButtons report={r} compact />
                        {isAdmin && (
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={`Delete ${r.number}`}
                            title="Delete"
                            onClick={() => setDeleting(r)}
                          >
                            <Trash2 />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <DeleteReportDialog report={deleting} onClose={() => setDeleting(null)} />
    </>
  );
}
