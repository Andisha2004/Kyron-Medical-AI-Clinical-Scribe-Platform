import type { Metadata } from "next";

import { PageHeader } from "@/components/ui/page-header";

export const metadata: Metadata = {
  title: "Note Templates",
};

export default function AdminTemplatesPage() {
  return (
    <div>
      <PageHeader
        title="Note templates"
        description="Manage SOAP note templates and organization-specific documentation rules."
      />

      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6">
        <p className="text-sm text-slate-600">
          Template management will be implemented during the template workflow task.
        </p>
      </div>
    </div>
  );
}
