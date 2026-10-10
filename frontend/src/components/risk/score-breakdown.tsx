import { ExternalLink } from "lucide-react";

import type { RiskBreakdown, RiskComponent } from "@/lib/types";
import { cn } from "@/lib/utils";

// Severity of a single item. "low" is deliberately neutral grey: green would read as
// "fine", and green is reserved for the Low risk *band*.
const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-risk-critical",
  high: "bg-risk-high",
  medium: "bg-risk-medium",
  low: "bg-muted-foreground/50",
  info: "bg-muted-foreground/25",
};

/** "Why this score": every component, every point, and the evidence behind it. */
export function ScoreBreakdown({ risk }: { risk: RiskBreakdown }) {
  return (
    <div className="space-y-5">
      <div className="rounded-lg bg-muted/60 px-3 py-2 font-mono text-xs leading-relaxed break-words">
        {risk.formula}
      </div>
      {risk.components.map((c) => (
        <ComponentRow key={c.key} component={c} />
      ))}
      <div className="flex items-center justify-between border-t pt-3 text-sm">
        <span className="text-muted-foreground">
          Criticality {risk.criticality}/12 multiplier
        </span>
        <span className="font-medium tabular-nums">x {risk.multiplier}</span>
      </div>
    </div>
  );
}

function ComponentRow({ component: c }: { component: RiskComponent }) {
  const capped = c.uncapped > c.cap;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">{c.label}</span>
        <span className="tabular-nums">
          <span className="font-semibold">{c.points}</span>
          <span className="text-muted-foreground"> / {c.cap}</span>
        </span>
      </div>
      {/* neutral fill: this is an amount, not a status */}
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-foreground/60" style={{ width: `${(c.points / c.cap) * 100}%` }} />
      </div>
      {c.items.length === 0 ? (
        <p className="text-xs text-muted-foreground">Nothing found.</p>
      ) : (
        <ul className="space-y-1.5">
          {c.items.map((item, i) => (
            <li key={i} className="flex gap-2 text-xs">
              <span className={cn("mt-1 size-1.5 shrink-0 rounded-full", SEVERITY_DOT[item.severity] ?? SEVERITY_DOT.info)} />
              <div className="min-w-0 flex-1">
                <p>
                  {item.cve_id ? (
                    <a
                      href={`https://nvd.nist.gov/vuln/detail/${item.cve_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-0.5 font-medium underline-offset-2 hover:underline"
                    >
                      {item.label}
                      <ExternalLink className="size-3 text-muted-foreground" />
                    </a>
                  ) : (
                    item.label
                  )}
                </p>
                {item.detail && <p className="text-muted-foreground">{item.detail}</p>}
              </div>
              <span className="shrink-0 font-medium tabular-nums">+{item.points}</span>
            </li>
          ))}
        </ul>
      )}
      {capped && (
        <p className="text-xs text-muted-foreground">
          Found {c.uncapped} points; this part of the score is capped at {c.cap}.
        </p>
      )}
    </div>
  );
}
