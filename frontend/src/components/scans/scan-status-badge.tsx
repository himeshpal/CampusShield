import { Badge } from "@/components/ui/badge";
import type { ScanStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STYLES: Record<ScanStatus, { label: string; className: string; dot: string }> = {
  queued: { label: "Queued", className: "text-muted-foreground", dot: "bg-muted-foreground" },
  running: {
    label: "Running",
    className: "border-primary/30 bg-primary/10 text-primary",
    dot: "bg-primary animate-pulse",
  },
  completed: { label: "Completed", className: "", dot: "bg-primary" },
  failed: {
    label: "Failed",
    className: "border-risk-critical/30 bg-risk-critical/10 text-risk-critical-ink",
    dot: "bg-risk-critical",
  },
  cancelled: { label: "Cancelled", className: "text-muted-foreground", dot: "bg-muted-foreground" },
};

export function ScanStatusBadge({ status }: { status: ScanStatus }) {
  const style = STYLES[status];
  return (
    <Badge variant="outline" className={cn("gap-1.5", style.className)}>
      <span className={cn("size-1.5 rounded-full", style.dot)} />
      {style.label}
    </Badge>
  );
}

export const PROFILE_LABELS: Record<string, string> = {
  quick: "Quick",
  standard: "Standard",
  deep: "Deep",
};
