"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { Asset, AssetDetail, AssetFields, AssetStatus, AssetSummary, AssetType } from "@/lib/types";

export type AssetFilters = { status?: AssetStatus; asset_type?: AssetType; q?: string };

export function useAssets(filters: AssetFilters) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
  return useQuery({
    queryKey: ["assets", "list", filters],
    queryFn: () => api<Asset[]>(`/assets?${params}`),
    placeholderData: (previous) => previous,
  });
}

export function useAssetSummary() {
  return useQuery({
    queryKey: ["assets", "summary"],
    queryFn: () => api<AssetSummary>("/assets/summary"),
  });
}

export function useAsset(id: number) {
  return useQuery({
    queryKey: ["assets", "detail", id],
    queryFn: () => api<AssetDetail>(`/assets/${id}`),
  });
}

/** Create, update or register an asset; refreshes every asset view afterwards. */
export function useSaveAsset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      mode,
      id,
      fields,
    }: {
      mode: "create" | "edit" | "register";
      id?: number;
      fields: AssetFields | Partial<Asset>;
    }) => {
      if (mode === "create") return api<Asset>("/assets", { method: "POST", json: fields });
      if (mode === "register")
        return api<Asset>(`/assets/${id}/register`, { method: "POST", json: fields });
      return api<Asset>(`/assets/${id}`, { method: "PATCH", json: fields });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets"] });
      queryClient.invalidateQueries({ queryKey: ["scans", "detail"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
  });
}
