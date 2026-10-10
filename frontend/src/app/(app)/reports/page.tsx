import { FileText } from "lucide-react";
import type { Metadata } from "next";

import { ComingSoon } from "@/components/coming-soon";

export const metadata: Metadata = { title: "Reports" };

export default function Page() {
  return (
    <ComingSoon
      title="Reports"
      description="Audit-ready PDF summaries for the institution."
      icon={FileText}
      phase={6}
      points={[
        "Campus-wide risk summary and asset-by-asset detail",
        "Prioritised recommendations",
        "Report history with downloads",
      ]}
    />
  );
}
