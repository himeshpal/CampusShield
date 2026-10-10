import { ClipboardCheck } from "lucide-react";
import type { Metadata } from "next";

import { ComingSoon } from "@/components/coming-soon";

export const metadata: Metadata = { title: "Security checklist" };

export default function Page() {
  return (
    <ComingSoon
      title="Security checklist"
      description="Controls a network scan cannot verify."
      icon={ClipboardCheck}
      phase={5}
      points={[
        "Firewall, antivirus, disk encryption, MFA, patching, default credentials",
        "Evidence notes per asset and control",
        "Risk score updates as soon as a control changes",
      ]}
    />
  );
}
