import type { Metadata } from "next";

import { PageHeader } from "@/components/ui/page-header";

export const metadata: Metadata = {
  title: "Admin Dashboard",
};

const adminCards = [
  { label: "Active providers", value: "0" },
  { label: "Total encounters", value: "0" },
  { label: "Active templates", value: "0" },
];

export default function AdminDashboardPage() {
  return (
    <div>
      <PageHeader
        title="Administration"
        description="Manage providers, encounters, templates, and system configuration."
      />

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {adminCards.map((card) => (
          <article
            key={card.label}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm font-medium text-slate-600">{card.label}</p>
            <p className="mt-3 text-3xl font-bold text-slate-950">{card.value}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
