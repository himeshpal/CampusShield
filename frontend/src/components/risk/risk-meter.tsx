import { BAND_ORDER, BANDS, formatScore } from "@/lib/risk";
import type { RiskBand } from "@/lib/types";
import { cn } from "@/lib/utils";

/** A single score against the 0-100 scale: band segments as a track, a marker at the
 *  score, and the band named in text. */
export function RiskMeter({ score, band }: { score: number; band: RiskBand }) {
  const b = BANDS[band];
  const Icon = b.icon;
  return (
    <div className="space-y-3">
      <div className="flex items-end justify-between gap-4">
        <div className="flex items-baseline gap-2">
          <span className="text-5xl font-semibold tracking-tight">{formatScore(score)}</span>
          <span className="text-sm text-muted-foreground">/ 100</span>
        </div>
        <span className={cn("flex items-center gap-1.5 text-sm font-medium", b.ink)}>
          <Icon className="size-4" />
          {b.label} risk
        </span>
      </div>
      <div className="relative pt-1" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={score} aria-label="Risk score">
        <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full">
          {BAND_ORDER.map((name, i) => {
            const from = BANDS[name].from;
            const to = i < BAND_ORDER.length - 1 ? BANDS[BAND_ORDER[i + 1]!].from : 100;
            return (
              <div
                key={name}
                className={cn(BANDS[name].mark, name === band ? "opacity-100" : "opacity-25")}
                style={{ width: `${to - from}%` }}
              />
            );
          })}
        </div>
        {/* marker with a surface ring so it reads on any segment */}
        <div
          className="absolute top-0 size-4.5 -translate-x-1/2 rounded-full border-[3px] border-card bg-foreground shadow"
          style={{ left: `${Math.min(100, Math.max(0, score))}%` }}
          aria-hidden
        />
        <div className="mt-1.5 flex justify-between text-[11px] tabular-nums text-muted-foreground">
          <span>0</span>
          <span>25</span>
          <span>50</span>
          <span>75</span>
          <span>100</span>
        </div>
      </div>
    </div>
  );
}
