import type { Metadata } from "next";

import { PageHeader } from "@/components/ui/page-header";

export const metadata: Metadata = {
  title: "Manage Providers",
};

export default function AdminProvidersPage() {
  return (
    <div>
      <PageHeader
        title="Manage providers"
        description="Create, activate, deactivate, and review provider accounts."
      />

      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6">
        <p className="text-sm text-slate-600">
          Provider administration will be implemented after authentication and authorization are
          available.
        </p>
      </div>
    </div>
  );
}
