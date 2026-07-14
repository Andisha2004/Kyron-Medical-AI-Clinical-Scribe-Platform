import type { Metadata } from "next";

import { PageHeader } from "@/components/ui/page-header";

export const metadata: Metadata = {
  title: "Manage Encounters",
};

export default function AdminEncountersPage() {
  return (
    <div>
      <PageHeader
        title="Manage encounters"
        description="Review encounter activity and processing status across providers."
      />

      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6">
        <p className="text-sm text-slate-600">
          Encounter administration will be connected after the backend is available.
        </p>
      </div>
    </div>
  );
}
