"use client";

import { useEffect, useState } from "react";

type Health = { status: string; database: string; nmap: string };

const rows: { key: keyof Health; label: string }[] = [
  { key: "status", label: "Backend API" },
  { key: "database", label: "Database" },
  { key: "nmap", label: "Nmap scanner" },
];

export function SystemStatus() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("/api/v1/health")
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then(setHealth)
      .catch(() => setError(true));
  }, []);

  return (
    <div className="rounded-xl border bg-card p-5 shadow-sm">
      <h2 className="mb-4 text-sm font-medium text-muted-foreground">System status</h2>
      <ul className="space-y-3">
        {rows.map(({ key, label }) => {
          const value = error ? "unreachable" : health?.[key];
          const ok = value === "ok";
          return (
            <li key={key} className="flex items-center justify-between text-sm">
              <span>{label}</span>
              <span className="flex items-center gap-2 font-medium">
                <span
                  className={`size-2 rounded-full ${
                    value === undefined ? "animate-pulse bg-muted-foreground/40" : ok ? "bg-primary" : "bg-risk-critical"
                  }`}
                />
                <span className={ok ? "text-primary" : "text-muted-foreground"}>{value ?? "checking…"}</span>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
