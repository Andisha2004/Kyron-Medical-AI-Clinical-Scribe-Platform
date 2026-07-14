"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/page-header";
import { ApiError } from "@/lib/api";
import { getAdminDashboard } from "@/lib/admin";
import type { AdminDashboardResponse } from "@/types/admin";

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function AdminDashboardPage() {
  const [dashboard, setDashboard] = useState<AdminDashboardResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      try {
        const response = await getAdminDashboard();
        if (isMounted) {
          setDashboard(response);
        }
      } catch (error) {
        if (!isMounted) {
          return;
        }

        if (error instanceof ApiError) {
          setErrorMessage(error.message);
        } else if (error instanceof Error) {
          setErrorMessage(error.message);
        } else {
          setErrorMessage("Unable to load the admin dashboard.");
        }
      }
    }

    void loadDashboard();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div>
      <PageHeader
        title="Administration"
        description="Manage providers, encounters, templates, and system configuration."
      />

      {errorMessage ? (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      ) : null}

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {[
          { label: "Active providers", value: dashboard?.active_provider_count ?? "..." },
          { label: "Total encounters", value: dashboard?.total_encounter_count ?? "..." },
          { label: "Active templates", value: dashboard?.active_template_count ?? "..." },
        ].map((card) => (
          <article
            key={card.label}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <p className="text-sm font-medium text-slate-600">{card.label}</p>
            <p className="mt-3 text-3xl font-bold text-slate-950">{card.value}</p>
          </article>
        ))}
      </div>

      <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-semibold text-slate-950">Recent encounters</h2>
          <div className="flex gap-3 text-sm">
            <Link className="text-slate-700 hover:text-slate-950" href="/admin/providers">
              Providers
            </Link>
            <Link className="text-slate-700 hover:text-slate-950" href="/admin/encounters">
              Encounters
            </Link>
            <Link className="text-slate-700 hover:text-slate-950" href="/admin/templates">
              Templates
            </Link>
          </div>
        </div>

        {!dashboard || dashboard.recent_encounters.length === 0 ? (
          <p className="mt-4 text-sm text-slate-600">No recent encounters available.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-slate-500">
                <tr>
                  <th className="pb-3 font-medium">Patient</th>
                  <th className="pb-3 font-medium">Provider</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Template</th>
                  <th className="pb-3 font-medium">Encounter date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {dashboard.recent_encounters.map((encounter) => (
                  <tr key={encounter.id}>
                    <td className="py-3 font-medium text-slate-900">{encounter.patient_name}</td>
                    <td className="py-3 text-slate-700">{encounter.provider_name}</td>
                    <td className="py-3 text-slate-700 capitalize">{encounter.status}</td>
                    <td className="py-3 text-slate-700">{encounter.template_name}</td>
                    <td className="py-3 text-slate-700">
                      {formatDateTime(encounter.encounter_date)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
