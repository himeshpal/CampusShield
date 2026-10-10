import {
  Box,
  Cctv,
  Fingerprint,
  Monitor,
  Network,
  Printer,
  Server,
  Wifi,
  type LucideIcon,
} from "lucide-react";

import type { Asset, AssetFields, AssetType } from "@/lib/types";

export const ASSET_TYPES: { value: AssetType; label: string; icon: LucideIcon }[] = [
  { value: "server", label: "Server", icon: Server },
  { value: "workstation", label: "Workstation", icon: Monitor },
  { value: "wifi_ap", label: "Wi-Fi access point", icon: Wifi },
  { value: "iot_cctv", label: "CCTV camera", icon: Cctv },
  { value: "iot_biometric", label: "Biometric device", icon: Fingerprint },
  { value: "printer", label: "Printer", icon: Printer },
  { value: "network_device", label: "Network device", icon: Network },
  { value: "other", label: "Other", icon: Box },
];

export function assetType(value: AssetType) {
  return ASSET_TYPES.find((t) => t.value === value) ?? ASSET_TYPES[ASSET_TYPES.length - 1]!;
}

/** Objective valuation criteria (Ete et al., 2024), each rated 1-3. */
export const CRITERIA = [
  {
    key: "data_sensitivity",
    label: "Data sensitivity",
    hint: "How sensitive is the data it stores or processes?",
  },
  {
    key: "service_dependency",
    label: "Service dependency",
    hint: "How many campus services stop if it fails?",
  },
  { key: "users_affected", label: "Users affected", hint: "How many people rely on it?" },
  {
    key: "replaceability",
    label: "Replaceability",
    hint: "How hard is it to replace or restore?",
  },
] as const satisfies readonly { key: keyof AssetFields; label: string; hint: string }[];

export const LEVELS = ["Low", "Medium", "High"] as const;

export function displayName(asset: Pick<Asset, "name" | "hostname" | "ip_address">): string {
  return asset.name ?? asset.hostname ?? asset.ip_address ?? "Unnamed device";
}

export function criticalityTotal(fields: Pick<AssetFields, (typeof CRITERIA)[number]["key"]>) {
  return CRITERIA.reduce((sum, c) => sum + fields[c.key], 0);
}

export function criticalityLevel(total: number): "low" | "medium" | "high" {
  return total >= 10 ? "high" : total >= 7 ? "medium" : "low";
}

/** Ports seen on the network that are not in the asset's expected baseline. */
export function unexpectedPorts(asset: Pick<Asset, "baseline_ports" | "observed_ports">) {
  if (!asset.observed_ports) return [];
  const baseline = new Set(asset.baseline_ports);
  return asset.observed_ports.filter((p) => !baseline.has(p.port));
}
