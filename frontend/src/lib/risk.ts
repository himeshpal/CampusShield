import { OctagonAlert, ShieldAlert, ShieldCheck, ShieldMinus, type LucideIcon } from "lucide-react";

import type { RiskBand } from "@/lib/types";

/** Risk bands are a status scale: every use pairs the colour with the band's name
 *  (and here an icon), so meaning never rests on colour alone. */
export const BANDS: Record<
  RiskBand,
  { label: string; from: number; mark: string; ink: string; tint: string; icon: LucideIcon }
> = {
  low: { label: "Low", from: 0, mark: "bg-risk-low", ink: "text-risk-low-ink", tint: "bg-risk-low/10", icon: ShieldCheck },
  medium: { label: "Medium", from: 25, mark: "bg-risk-medium", ink: "text-risk-medium-ink", tint: "bg-risk-medium/15", icon: ShieldMinus },
  high: { label: "High", from: 50, mark: "bg-risk-high", ink: "text-risk-high-ink", tint: "bg-risk-high/15", icon: ShieldAlert },
  critical: { label: "Critical", from: 75, mark: "bg-risk-critical", ink: "text-risk-critical-ink", tint: "bg-risk-critical/10", icon: OctagonAlert },
};

export const BAND_ORDER: RiskBand[] = ["low", "medium", "high", "critical"];

/** CSS variable for a band's mark colour, for SVG/chart fills. */
export function bandColor(band: RiskBand): string {
  return `var(--risk-${band})`;
}

export function formatScore(score: number): string {
  return String(Math.round(score));
}
