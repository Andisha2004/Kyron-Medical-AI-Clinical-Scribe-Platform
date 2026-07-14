import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/ui/page-header";

export const metadata: Metadata = {
  title: "Encounters",
};

export default function EncountersPage() {
  return (
    <div>
      <PageHeader
        title="Encounters"
        description="View, filter, and continue clinical encounter documentation."
        actions={
          <Link
            href="/provider/encounters/new"
            className="inline-flex min-h-10 items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
          >
            New encounter
          </Link>
        }
      />

      <section className="mt-8 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="font-semibold text-slate-950">Encounter history</h2>
        </div>

        <div className="p-8 text-center">
          <p className="text-sm text-slate-600">No encounters have been created.</p>
        </div>
      </section>
    </div>
  );
}
