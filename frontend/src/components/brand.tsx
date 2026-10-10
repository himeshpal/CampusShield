import { ShieldCheck } from "lucide-react";

import { cn } from "@/lib/utils";

export function BrandMark({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm",
        className,
      )}
    >
      <ShieldCheck className="size-5" strokeWidth={2.25} />
    </div>
  );
}

export function Brand({ subtitle = "Security audit platform" }: { subtitle?: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <BrandMark />
      <div className="grid leading-tight">
        <span className="font-semibold tracking-tight">CampusShield</span>
        <span className="text-xs text-muted-foreground">{subtitle}</span>
      </div>
    </div>
  );
}
