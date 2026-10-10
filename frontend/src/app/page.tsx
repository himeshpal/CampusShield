import { ShieldCheck } from "lucide-react";

import { SystemStatus } from "@/components/system-status";

// Step 0 landing page: proves Next.js -> /api proxy -> FastAPI -> Postgres/nmap all connect.
// Replaced by the login + dashboard shell in Phase 1.
export default function Home() {
  return (
    <main className="flex flex-1 items-center justify-center bg-muted/40 px-4 py-16">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <ShieldCheck className="size-5" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight">CampusShield</h1>
            <p className="text-sm text-muted-foreground">Campus cybersecurity audit platform</p>
          </div>
        </div>
        <SystemStatus />
      </div>
    </main>
  );
}
