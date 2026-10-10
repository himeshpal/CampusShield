"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { toast } from "sonner";

import { api } from "@/lib/api";
import type { Scan, ScanOptions } from "@/lib/types";

const POLL_MS = 1500;

export function useScanOptions() {
  return useQuery({
    queryKey: ["scans", "options"],
    queryFn: () => api<ScanOptions>("/scans/options"),
    staleTime: Infinity,
  });
}

export function useScanHistory(limit = 20) {
  return useQuery({
    queryKey: ["scans", "list", limit],
    queryFn: () => api<Scan[]>(`/scans?limit=${limit}`),
  });
}

/**
 * The scan currently queued/running (or null). Polls while one is active and, when it
 * finishes, refreshes the history and announces the result.
 */
export function useActiveScan() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["scans", "active"],
    queryFn: () => api<Scan | null>("/scans/active"),
    refetchInterval: (q) => (q.state.data ? POLL_MS : false),
  });

  const previous = useRef<Scan | null | undefined>(undefined);
  useEffect(() => {
    const before = previous.current;
    previous.current = query.data;
    if (before && query.data === null) {
      // the scan we were watching just finished
      queryClient.invalidateQueries({ queryKey: ["scans", "list"] });
      queryClient.invalidateQueries({ queryKey: ["scans", "detail", before.id] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
      api<Scan>(`/scans/${before.id}`).then((scan) => {
        if (scan.status === "completed") {
          toast.success(`Scan #${scan.id} completed`, {
            description: `${scan.hosts_up} hosts up, ${scan.open_ports} open ports`,
          });
        } else if (scan.status === "failed") {
          toast.error(`Scan #${scan.id} failed`, { description: scan.error ?? undefined });
        } else if (scan.status === "cancelled") {
          toast.info(`Scan #${scan.id} cancelled`);
        }
      });
    }
  }, [query.data, queryClient]);

  return query;
}
