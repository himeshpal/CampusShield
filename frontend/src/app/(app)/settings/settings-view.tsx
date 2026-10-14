"use client";

import { useRouter, useSearchParams } from "next/navigation";

import { PageHeader } from "@/components/page-header";
import { SystemStatus } from "@/components/system-status";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCurrentUser } from "@/hooks/use-current-user";

import { AuditLogPanel } from "./audit-log-panel";
import { NotificationsPanel } from "./notifications-panel";
import { RiskModelPanel } from "./risk-model-panel";
import { UsersPanel } from "./users-panel";

export function SettingsView() {
  const { user } = useCurrentUser();

  return (
    <>
      <PageHeader
        title="Settings"
        description="Accounts, audit trail, notifications, risk model and system health."
      />
      {user ? <SettingsTabs userId={user.id} isAdmin={user.role === "admin"} /> : <TabsSkeleton />}
    </>
  );
}

const TAB_KEYS = ["users", "audit", "notifications", "risk", "system"];

function SettingsTabs({ userId, isAdmin }: { userId: number; isAdmin: boolean }) {
  const params = useSearchParams();
  const router = useRouter();
  const requested = params.get("tab");
  const fallback = isAdmin ? "users" : "audit";
  const tab =
    requested && TAB_KEYS.includes(requested) && (requested !== "users" || isAdmin)
      ? requested
      : fallback;
  return (
    <Tabs
      value={tab}
      onValueChange={(v) => router.replace(v === fallback ? "/settings" : `/settings?tab=${v}`, { scroll: false })}
      className="gap-4"
    >
      {/* five tabs are wider than a phone: the bar scrolls instead of the page */}
      <TabsList className="max-w-full justify-start overflow-x-auto">
        {isAdmin && <TabsTrigger value="users">Users</TabsTrigger>}
        <TabsTrigger value="audit">Audit log</TabsTrigger>
        <TabsTrigger value="notifications">Notifications</TabsTrigger>
        <TabsTrigger value="risk">Risk model</TabsTrigger>
        <TabsTrigger value="system">System</TabsTrigger>
      </TabsList>
      {isAdmin && (
        <TabsContent value="users">
          <UsersPanel currentUserId={userId} />
        </TabsContent>
      )}
      <TabsContent value="audit">
        <AuditLogPanel />
      </TabsContent>
      <TabsContent value="notifications">
        <NotificationsPanel isAdmin={isAdmin} />
      </TabsContent>
      <TabsContent value="risk">
        <RiskModelPanel />
      </TabsContent>
      <TabsContent value="system">
        <div className="max-w-md">
          <SystemStatus />
        </div>
      </TabsContent>
    </Tabs>
  );
}

function TabsSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-56" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  );
}
