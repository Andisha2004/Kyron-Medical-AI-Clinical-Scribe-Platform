import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/ui/page-header";

export const metadata: Metadata = {
  title: "Provider Dashboard",
};

const summaryCards = [
  { label: "Draft encounters", value: "0" },
  { label: "Ready for review", value: "0" },
  { label: "Completed today", value: "0" },
];

export default function ProviderDashboardPage() {
  return (
    <div>
      <PageHeader
        title="Provider dashboard"
        description="Review recent encounters and start new clinical documentation workflows."
        actions={
          <Link
            href="/provider/encounters/new"
            className="inline-flex min-h-10 items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
          >
            New encounter
          </Link>
        }
      />

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {summaryCards.map((card) => (
          <article
            key={card.label}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm font-medium text-slate-600">{card.label}</p>
            <p className="mt-3 text-3xl font-bold text-slate-950">{card.value}</p>
          </article>
        ))}
      </div>

      <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="font-semibold text-slate-950">Recent encounters</h2>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          No encounters are available. Encounter data will appear after the backend and database
          integrations are implemented.
        </p>
      </section>
    </div>
  );
}
