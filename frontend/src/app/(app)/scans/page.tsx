import { Radar } from "lucide-react";
import type { Metadata } from "next";

import { ComingSoon } from "@/components/coming-soon";

export const metadata: Metadata = { title: "Network scans" };

export default function Page() {
  return (
    <ComingSoon
      title="Network scans"
      description="Discover live hosts, open ports and running services."
      icon={Radar}
      phase={2}
      points={[
        "Quick, standard and deep Nmap scan profiles",
        "Live progress while the scan runs",
        "Scope guard: only authorised subnets can be scanned",
      ]}
    />
  );
}
