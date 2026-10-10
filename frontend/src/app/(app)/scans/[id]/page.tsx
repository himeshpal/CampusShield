import type { Metadata } from "next";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { ScanDetailView } from "./scan-detail-view";

export const metadata: Metadata = { title: "Scan results" };

// The scan id is only known at request time, so the view streams in behind Suspense
// while the surrounding shell is prerendered (Cache Components).
export default function ScanDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-24 w-full rounded-xl" />
        </div>
      }
    >
      <ScanDetailView />
    </Suspense>
  );
}
