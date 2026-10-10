import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { BAND_ORDER, BANDS } from "@/lib/risk";
import type { RiskBand } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Part-to-whole across the four bands: one stacked bar (2px surface gaps between
 *  segments) plus a legend that names every band with its count. */
export function RiskDistribution({ bands }: { bands: Record<RiskBand, number> }) {
  const total = BAND_ORDER.reduce((sum, b) => sum + bands[b], 0);
  const order = [...BAND_ORDER].reverse(); // critical first: what needs attention

  return (
    <div className="space-y-4">
      <div className="flex h-6 gap-0.5" role="img" aria-label="Assets by risk band">
        {total === 0 && <div className="h-full w-full rounded-md bg-muted" />}
        {order
          .filter((b) => bands[b] > 0)
          .map((b, i, shown) => (
            <Tooltip key={b}>
              <TooltipTrigger asChild>
                <div
                  className={cn(
                    "h-full min-w-2 transition-opacity hover:opacity-85",
                    BANDS[b].mark,
                    i === 0 && "rounded-l-md",
                    i === shown.length - 1 && "rounded-r-md",
                  )}
                  style={{ width: `${(bands[b] / total) * 100}%` }}
                />
              </TooltipTrigger>
              <TooltipContent>
                {BANDS[b].label}: {bands[b]} of {total} assets
              </TooltipContent>
            </Tooltip>
          ))}
      </div>
      <ul className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
        {order.map((b) => {
          const Icon = BANDS[b].icon;
          return (
            <li key={b} className="flex items-center gap-2 text-sm">
              <span className={cn("size-2.5 shrink-0 rounded-sm", BANDS[b].mark)} aria-hidden />
              <Icon className="size-3.5 text-muted-foreground" aria-hidden />
              <span className="text-muted-foreground">{BANDS[b].label}</span>
              <span className="ml-auto font-semibold tabular-nums">{bands[b]}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
