import type { Metadata } from "next";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { AssetsView } from "./assets-view";

export const metadata: Metadata = { title: "Assets" };

// AssetsView reads ?status= from the URL, so it streams in behind Suspense.
export default function AssetsPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full rounded-xl" />}>
      <AssetsView />
    </Suspense>
  );
}
