import type { Metadata } from "next";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { SettingsView } from "./settings-view";

export const metadata: Metadata = { title: "Settings" };

// SettingsView reads ?tab= from the URL, so it streams in behind Suspense.
export default function SettingsPage() {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full rounded-xl" />}>
      <SettingsView />
    </Suspense>
  );
}
