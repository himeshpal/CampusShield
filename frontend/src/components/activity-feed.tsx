"use client";

import { useQuery } from "@tanstack/react-query";
import {
  KeyRound,
  LogIn,
  LogOut,
  ShieldAlert,
  UserMinus,
  UserPen,
  UserPlus,
  type LucideIcon,
} from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { actionLabel, timeAgo } from "@/lib/format";
import type { AuditEntry, Page } from "@/lib/types";
import { cn } from "@/lib/utils";

const ICONS: Record<string, LucideIcon> = {
  "auth.login": LogIn,
  "auth.logout": LogOut,
  "auth.login_failed": ShieldAlert,
  "user.created": UserPlus,
  "user.seeded": UserPlus,
  "user.updated": UserPen,
  "user.deleted": UserMinus,
};

export function ActivityFeed({ limit = 6 }: { limit?: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["audit-log", { limit }],
    queryFn: () => api<Page<AuditEntry>>(`/audit-log?limit=${limit}`),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="flex gap-3">
            <Skeleton className="size-8 rounded-full" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-2/3" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!data?.items.length) {
    return <p className="text-sm text-muted-foreground">No activity yet.</p>;
  }

  return (
    <ul className="space-y-4">
      {data.items.map((entry) => {
        const Icon = ICONS[entry.action] ?? KeyRound;
        const failed = entry.action.endsWith("_failed");
        return (
          <li key={entry.id} className="flex gap-3">
            <div
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-full",
                failed ? "bg-risk-critical/10 text-risk-critical" : "bg-muted text-muted-foreground",
              )}
            >
              <Icon className="size-4" />
            </div>
            <div className="min-w-0 text-sm">
              <p className="truncate">
                <span className="font-medium">{actionLabel(entry.action)}</span>
              </p>
              <p className="truncate text-xs text-muted-foreground">
                {entry.actor} · {timeAgo(entry.created_at)}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
