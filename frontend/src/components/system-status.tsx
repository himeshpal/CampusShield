"use client";

import { useQuery } from "@tanstack/react-query";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Health } from "@/lib/types";
import { cn } from "@/lib/utils";

const ROWS: { key: keyof Health; label: string }[] = [
  { key: "status", label: "Backend API" },
  { key: "database", label: "Database" },
  { key: "nmap", label: "Nmap scanner" },
];

export function SystemStatus() {
  const { data, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => api<Health>("/health"),
    refetchInterval: 30_000,
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>System status</CardTitle>
        <CardDescription>Checked every 30 seconds.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="divide-y">
          {ROWS.map(({ key, label }) => {
            const value = isError ? "unreachable" : data?.[key];
            const ok = value === "ok";
            return (
              <li key={key} className="flex items-center justify-between py-2.5 text-sm">
                <span>{label}</span>
                <span className="flex items-center gap-2 font-medium">
                  <span
                    className={cn(
                      "size-2 rounded-full",
                      value === undefined && "animate-pulse bg-muted-foreground/40",
                      value !== undefined && (ok ? "bg-primary" : "bg-risk-critical"),
                    )}
                  />
                  <span className={ok ? "text-primary" : "text-muted-foreground"}>
                    {value === undefined ? "checking…" : ok ? "Operational" : value}
                  </span>
                </span>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
