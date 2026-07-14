import type { ReactNode } from "react";

import { AuthGuard } from "@/components/auth/auth-guard";
import { LogoutButton } from "@/components/auth/logout-button";
import { DashboardSidebar } from "@/components/layout/dashboard-sidebar";

const providerNavigation = [
  { href: "/provider", label: "Dashboard" },
  { href: "/provider/encounters", label: "Encounters" },
  { href: "/provider/encounters/new", label: "New encounter" },
];

interface ProviderLayoutProps {
  children: ReactNode;
}

export default function ProviderLayout({ children }: ProviderLayoutProps) {
  return (
    <AuthGuard allowedRoles={["provider"]}>
      <DashboardSidebar title="Provider" items={providerNavigation} footer={<LogoutButton />}>
        {children}
      </DashboardSidebar>
    </AuthGuard>
  );
}
