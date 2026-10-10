"use client";

import { PageHeader } from "@/components/page-header";
import { SystemStatus } from "@/components/system-status";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCurrentUser } from "@/hooks/use-current-user";

import { AuditLogPanel } from "./audit-log-panel";
import { UsersPanel } from "./users-panel";

export function SettingsView() {
  const { user } = useCurrentUser();

  return (
    <>
      <PageHeader title="Settings" description="Accounts, audit trail and system health." />
      {user ? <SettingsTabs userId={user.id} isAdmin={user.role === "admin"} /> : <TabsSkeleton />}
    </>
  );
}

function SettingsTabs({ userId, isAdmin }: { userId: number; isAdmin: boolean }) {
  return (
    <Tabs defaultValue={isAdmin ? "users" : "audit"} className="gap-4">
      <TabsList>
        {isAdmin && <TabsTrigger value="users">Users</TabsTrigger>}
        <TabsTrigger value="audit">Audit log</TabsTrigger>
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
