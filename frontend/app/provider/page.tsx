import type { Metadata } from "next";
import { ProviderDashboard } from "@/components/encounter/provider-dashboard";

export const metadata: Metadata = {
  title: "Provider Dashboard",
};

export default function ProviderDashboardPage() {
  return <ProviderDashboard />;
}
