import type { ReactNode } from "react";

import { AuthGuard } from "@/components/auth/auth-guard";
import { LogoutButton } from "@/components/auth/logout-button";
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
    <AuthGuard allowedRoles={["admin"]}>
      <DashboardSidebar title="Administration" items={adminNavigation} footer={<LogoutButton />}>
        {children}
      </DashboardSidebar>
    </AuthGuard>
  );
}
