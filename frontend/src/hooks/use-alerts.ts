"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useHydrated } from "@/hooks/use-hydrated";
import { api } from "@/lib/api";
import type {
  Alert,
  AlertKind,
  AlertSeverity,
  AlertStatus,
  AlertSummary,
  NotificationSettings,
  Page,
} from "@/lib/types";

export type AlertFilters = {
  status?: AlertStatus;
  unresolved?: boolean;
  kind?: AlertKind;
  scan_id?: number;
  asset_id?: number;
  limit?: number;
};

export function useAlerts(filters: AlertFilters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== false) params.set(key, String(value));
  }
  return useQuery({
    queryKey: ["alerts", "list", filters],
    queryFn: () => api<Page<Alert>>(`/alerts?${params}`),
    placeholderData: (previous) => previous,
  });
}

/** Shared by the sidebar badge and the pages. The sidebar can fetch it before a page
 *  segment hydrates, so data is withheld until hydration (server HTML has none). */
export function useAlertSummary() {
  const hydrated = useHydrated();
  const query = useQuery({
    queryKey: ["alerts", "summary"],
    queryFn: () => api<AlertSummary>("/alerts/summary"),
  });
  return { ...query, data: hydrated ? query.data : undefined };
}

/** Acknowledge, resolve or acknowledge everything; refreshes every alert view. */
export function useAlertAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (
      action:
        | { type: "acknowledge"; id: number }
        | { type: "resolve"; id: number; note: string | null }
        | { type: "acknowledge-all" },
    ): Promise<number> => {
      // resolves to the number of alerts changed
      if (action.type === "acknowledge-all")
        return (await api<{ acknowledged: number }>("/alerts/acknowledge-all", { method: "POST" }))
          .acknowledged;
      if (action.type === "acknowledge")
        await api<Alert>(`/alerts/${action.id}/acknowledge`, { method: "POST" });
      else
        await api<Alert>(`/alerts/${action.id}/resolve`, { method: "POST", json: { note: action.note } });
      return 1;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

export function useNotificationSettings() {
  return useQuery({
    queryKey: ["alerts", "settings"],
    queryFn: () => api<NotificationSettings>("/alerts/settings"),
  });
}

export function useSaveNotificationSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (min_severity: AlertSeverity) =>
      api<NotificationSettings>("/alerts/settings", { method: "PUT", json: { min_severity } }),
    onSuccess: (data) => {
      queryClient.setQueryData(["alerts", "settings"], data);
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}

type SendResult = { state: "sent" | "failed" | "not_configured"; error: string | null };

/** A sample alert through backend -> n8n -> Telegram / email; or one alert again. */
export function useSendAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number | "test") =>
      api<SendResult>(id === "test" ? "/alerts/test" : `/alerts/${id}/notify`, { method: "POST" }),
    onSuccess: () => {
      // n8n reports the channel results a moment later
      setTimeout(() => queryClient.invalidateQueries({ queryKey: ["alerts"] }), 3000);
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}
