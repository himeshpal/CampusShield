"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Report } from "@/lib/types";

export function useReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: () => api<Report[]>("/reports"),
  });
}

/** Rendering takes a few seconds: the PDF is built on the server from the live data. */
export function useGenerateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string | null; include_details: boolean }) =>
      api<Report>("/reports", { method: "POST", json: body }),
    onSuccess: (report) => {
      queryClient.setQueryData<Report[]>(["reports"], (old) => old && [report, ...old]);
      queryClient.invalidateQueries({ queryKey: ["reports"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useDeleteReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/reports/${id}`, { method: "DELETE" }),
    onSuccess: (_, id) => {
      queryClient.setQueryData<Report[]>(["reports"], (old) => old?.filter((r) => r.id !== id));
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

/** Same-origin URL of a report's PDF (through the Next.js /api proxy, cookie included). */
export function reportPdfUrl(id: number, download = false): string {
  return `/api/v1/reports/${id}/pdf${download ? "?download=true" : ""}`;
}
