"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { actionLabel, dateTime } from "@/lib/format";
import type { AuditEntry, Page } from "@/lib/types";

const PAGE_SIZE = 15;
const FILTERS = [
  { value: "all", label: "All actions" },
  { value: "auth.", label: "Sign-ins" },
  { value: "user.", label: "User changes" },
  { value: "scan.", label: "Scans" },
  { value: "asset.", label: "Assets" },
];

export function AuditLogPanel() {
  const [filter, setFilter] = useState("all");
  const [page, setPage] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: ["audit-log", { filter, page }],
    queryFn: () => {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });
      if (filter !== "all") params.set("action", filter);
      return api<Page<AuditEntry>>(`/audit-log?${params}`);
    },
    placeholderData: keepPreviousData,
  });

  const total = data?.total ?? 0;
  const from = total === 0 ? 0 : page * PAGE_SIZE + 1;
  const to = Math.min(total, (page + 1) * PAGE_SIZE);

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1.5">
          <CardTitle>Audit log</CardTitle>
          <CardDescription>Every sign-in and change, newest first.</CardDescription>
        </div>
        <Select
          value={filter}
          onValueChange={(v) => {
            setFilter(v);
            setPage(0);
          }}
        >
          <SelectTrigger className="w-40" aria-label="Filter actions">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {FILTERS.map((f) => (
              <SelectItem key={f.value} value={f.value}>
                {f.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-44">When</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Target</TableHead>
              <TableHead className="text-right">IP address</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 5 }, (_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))}
            {data?.items.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell className="text-muted-foreground">{dateTime(entry.created_at)}</TableCell>
                <TableCell className="font-medium">{entry.actor}</TableCell>
                <TableCell>
                  {entry.action.endsWith("failed") ? (
                    <Badge variant="destructive">{actionLabel(entry.action)}</Badge>
                  ) : (
                    actionLabel(entry.action)
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {entry.entity_type ? `${entry.entity_type} #${entry.entity_id}` : "—"}
                </TableCell>
                <TableCell className="text-right font-mono text-xs text-muted-foreground">
                  {entry.ip_address ?? "—"}
                </TableCell>
              </TableRow>
            ))}
            {data && data.items.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="py-8 text-center text-muted-foreground">
                  No entries match this filter.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
          <span>
            {from}–{to} of {total}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="icon-sm"
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              aria-label="Previous page"
            >
              <ChevronLeft />
            </Button>
            <Button
              variant="outline"
              size="icon-sm"
              disabled={to >= total}
              onClick={() => setPage((p) => p + 1)}
              aria-label="Next page"
            >
              <ChevronRight />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
