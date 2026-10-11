"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type {
  ChecklistMatrix,
  ChecklistSaveResult,
  ChecklistSummary,
  ControlStatus,
} from "@/lib/types";

export function useChecklist() {
  return useQuery({
    queryKey: ["checklist", "matrix"],
    queryFn: () => api<ChecklistMatrix>("/checklist"),
  });
}

export function useChecklistSummary() {
  return useQuery({
    queryKey: ["checklist", "summary"],
    queryFn: () => api<ChecklistSummary>("/checklist/summary"),
  });
}

/** Save one control; the response carries the asset's risk before and after. */
export function useSaveControl() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      assetId,
      key,
      status,
      evidence,
    }: {
      assetId: number;
      key: string;
      status: ControlStatus;
      evidence: string | null;
    }) =>
      api<ChecklistSaveResult>(`/checklist/${assetId}/${key}`, {
        method: "PUT",
        json: { status, evidence },
      }),
    onSuccess: (result) => {
      // update the matrix row in place, then refresh everything the score feeds
      queryClient.setQueryData<ChecklistMatrix>(["checklist", "matrix"], (old) =>
        old && {
          ...old,
          rows: old.rows.map((r) => (r.asset_id === result.row.asset_id ? result.row : r)),
        },
      );
      queryClient.invalidateQueries({ queryKey: ["checklist", "summary"] });
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}
