import type { LucideIcon } from "lucide-react";

import { PageHeader } from "@/components/page-header";

// Placeholder for modules delivered in later build phases.
export function ComingSoon({
  title,
  description,
  icon: Icon,
  phase,
  points,
}: {
  title: string;
  description: string;
  icon: LucideIcon;
  phase: number;
  points: string[];
}) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed bg-muted/20 px-6 py-16 text-center">
        <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="size-6" />
        </div>
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-primary">
          Build phase {phase}
        </p>
        <h2 className="text-lg font-semibold">This module is on the way</h2>
        <ul className="mt-4 space-y-1.5 text-sm text-muted-foreground">
          {points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </div>
    </>
  );
}
