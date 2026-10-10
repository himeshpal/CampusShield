import {
  Bell,
  ClipboardCheck,
  FileText,
  LayoutDashboard,
  Radar,
  Server,
  Settings,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  /** Build phase that delivers the page; shown as "Soon" until then. */
  phase?: number;
};

export const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: "Overview",
    items: [{ title: "Dashboard", href: "/dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Inventory",
    items: [
      { title: "Assets", href: "/assets", icon: Server, phase: 3 },
      { title: "Network scans", href: "/scans", icon: Radar },
    ],
  },
  {
    label: "Security",
    items: [
      { title: "Checklist", href: "/checklist", icon: ClipboardCheck, phase: 5 },
      { title: "Alerts", href: "/alerts", icon: Bell, phase: 7 },
      { title: "Reports", href: "/reports", icon: FileText, phase: 6 },
    ],
  },
  {
    label: "System",
    items: [{ title: "Settings", href: "/settings", icon: Settings }],
  },
];

export const ALL_NAV_ITEMS = NAV_GROUPS.flatMap((g) => g.items);

export function isActive(item: NavItem, pathname: string | null): boolean {
  return !!pathname && (pathname === item.href || pathname.startsWith(`${item.href}/`));
}
