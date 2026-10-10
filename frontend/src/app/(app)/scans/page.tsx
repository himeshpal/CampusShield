import type { Metadata } from "next";

import { ScansView } from "./scans-view";

export const metadata: Metadata = { title: "Network scans" };

export default function ScansPage() {
  return <ScansView />;
}
