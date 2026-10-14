"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";

// Everything the dashboard shows; scans and checklist answers can change from another
// browser (or, from Phase 7, a scheduled n8n scan), so the overview re-reads them.
const LIVE_KEYS = [["assets"], ["checklist"], ["scans"], ["reports"], ["audit-log"]];

/** Keep the page live: refetch its data every `intervalMs` while the tab is visible,
 *  and immediately when the user comes back to the tab. */
export function useLiveRefresh(intervalMs = 30_000) {
  const queryClient = useQueryClient();
  useEffect(() => {
    const refresh = () => {
      if (document.visibilityState !== "visible") return;
      for (const queryKey of LIVE_KEYS) queryClient.invalidateQueries({ queryKey });
    };
    const timer = window.setInterval(refresh, intervalMs);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [queryClient, intervalMs]);
}
