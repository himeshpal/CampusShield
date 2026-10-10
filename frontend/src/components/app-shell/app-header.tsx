"use client";

import { usePathname } from "next/navigation";
import { Suspense } from "react";

import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";

import { ALL_NAV_ITEMS, isActive } from "./nav";
import { ThemeToggle } from "./theme-toggle";

export function AppHeader() {
  return (
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur">
      <SidebarTrigger className="-ml-1" />
      <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
      {/* reads the URL, so it streams in on dynamic routes */}
      <Suspense fallback={<span className="text-sm font-medium">CampusShield</span>}>
        <PageTitle />
      </Suspense>
      <div className="ml-auto flex items-center gap-1">
        <ThemeToggle />
      </div>
    </header>
  );
}

function PageTitle() {
  const pathname = usePathname();
  const current = ALL_NAV_ITEMS.find((item) => isActive(item, pathname));
  return <span className="text-sm font-medium">{current?.title ?? "CampusShield"}</span>;
}
