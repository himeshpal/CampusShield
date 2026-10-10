import type { Metadata } from "next";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { AssetDetailView } from "./asset-detail-view";

export const metadata: Metadata = { title: "Asset" };

export default function AssetPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-64 w-full rounded-xl" />
        </div>
      }
    >
      <AssetDetailView />
    </Suspense>
  );
}
