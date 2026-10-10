import { Badge } from "@/components/ui/badge";
import { BANDS, formatScore } from "@/lib/risk";
import type { RiskBand } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Score + band name; the colour sits on the dot, the text stays in ink. */
export function RiskBadge({
  score,
  band,
  className,
}: {
  score: number | null;
  band: RiskBand | null;
  className?: string;
}) {
  if (score === null || band === null) {
    return <span className="text-xs text-muted-foreground">Not assessed</span>;
  }
  const b = BANDS[band];
  return (
    <Badge
      variant="outline"
      className={cn("gap-1.5 font-normal", className)}
      title={`Risk ${score} / 100 (${b.label})`}
    >
      <span className={cn("size-2 rounded-full", b.mark)} aria-hidden />
      <span className="font-semibold tabular-nums">{formatScore(score)}</span>
      <span className="text-muted-foreground">{b.label}</span>
    </Badge>
  );
}
