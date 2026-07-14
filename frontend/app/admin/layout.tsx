import type { ReactNode } from "react";

import { DashboardSidebar } from "@/components/layout/dashboard-sidebar";

const adminNavigation = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/encounters", label: "Encounters" },
  { href: "/admin/providers", label: "Providers" },
  { href: "/admin/templates", label: "Templates" },
];

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <DashboardSidebar title="Administration" items={adminNavigation}>
      {children}
    </DashboardSidebar>
  );
}
