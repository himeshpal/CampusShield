import { Server } from "lucide-react";
import type { Metadata } from "next";

import { ComingSoon } from "@/components/coming-soon";

export const metadata: Metadata = { title: "Assets" };

export default function Page() {
  return (
    <ComingSoon
      title="Assets"
      description="Persistent inventory of every campus IT device."
      icon={Server}
      phase={3}
      points={[
        "Searchable inventory with department, owner and criticality",
        "Automatic matching of scan results by MAC and IP",
        "Unregistered devices flagged and registered in one click",
      ]}
    />
  );
}
