"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense } from "react";

import { Brand } from "@/components/brand";
import { useAlertSummary } from "@/hooks/use-alerts";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar";

import { isActive, NAV_GROUPS } from "./nav";
import { UserMenu } from "./user-menu";

export function AppSidebar() {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-3 py-3">
        <Link href="/dashboard" className="group-data-[collapsible=icon]:-ml-0.5">
          <Brand />
        </Link>
      </SidebarHeader>

      <SidebarContent>
        {/* the active-link highlight reads the URL; on dynamic routes (/scans/[id]) that
            value only exists at request time, so it streams in behind Suspense */}
        <Suspense fallback={<NavGroups pathname={null} />}>
          <ActiveNavGroups />
        </Suspense>
      </SidebarContent>

      <SidebarFooter>
        <UserMenu />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

function ActiveNavGroups() {
  return <NavGroups pathname={usePathname()} />;
}

function NavGroups({ pathname }: { pathname: string | null }) {
  const { data: alerts } = useAlertSummary();
  const open = alerts?.open ?? 0;
  return NAV_GROUPS.map((group) => (
    <SidebarGroup key={group.label}>
      <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {group.items.map((item) => (
            <SidebarMenuItem key={item.href}>
              <SidebarMenuButton asChild tooltip={item.title} isActive={isActive(item, pathname)}>
                <Link href={item.href}>
                  <item.icon />
                  <span>{item.title}</span>
                </Link>
              </SidebarMenuButton>
              {item.href === "/alerts" && open > 0 && (
                <SidebarMenuBadge
                  className="rounded-full bg-risk-critical/10 px-1.5 text-risk-critical-ink"
                  aria-label={`${open} open alerts`}
                >
                  {open}
                </SidebarMenuBadge>
              )}
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  ));
}
