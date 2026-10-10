import { Bell } from "lucide-react";
import type { Metadata } from "next";

import { ComingSoon } from "@/components/coming-soon";

export const metadata: Metadata = { title: "Alerts" };

export default function Page() {
  return (
    <ComingSoon
      title="Alerts"
      description="Changes detected between scans."
      icon={Bell}
      phase={7}
      points={[
        "New devices, opened or closed ports, risk-score jumps",
        "Telegram and email delivery through n8n",
        "Acknowledge and resolve workflow",
      ]}
    />
  );
}
