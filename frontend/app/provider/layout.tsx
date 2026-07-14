import type { ReactNode } from "react";

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
    <DashboardSidebar title="Provider" items={providerNavigation}>
      {children}
    </DashboardSidebar>
  );
}
