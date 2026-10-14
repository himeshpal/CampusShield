import type { Metadata } from "next";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { AlertsView } from "./alerts-view";

export const metadata: Metadata = { title: "Alerts" };

// AlertsView reads ?status= and ?focus= (links in notifications) from the URL.
export default function AlertsPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full rounded-xl" />}>
      <AlertsView />
    </Suspense>
  );
}
