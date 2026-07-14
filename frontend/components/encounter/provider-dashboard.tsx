"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { ApiError } from "@/lib/api";
import { getProviderDashboard } from "@/lib/encounters";
import type { ProviderDashboardResponse } from "@/types/encounter";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ProviderDashboard() {
  const [dashboard, setDashboard] = useState<ProviderDashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboard() {
      try {
        const response = await getProviderDashboard();
        if (!isMounted) {
          return;
        }

        setDashboard(response);
        setError(null);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }

        if (loadError instanceof ApiError) {
          setError(loadError.message);
        } else if (loadError instanceof Error) {
          setError(loadError.message);
        } else {
          setError("Unable to load the provider dashboard.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
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
        title="Provider dashboard"
        description={
          dashboard
            ? `Welcome, ${dashboard.provider_name}. Review recent drafts and completed encounters.`
            : "Review recent encounters and start new clinical documentation workflows."
        }
        actions={
          <Link
            href="/provider/encounters/new"
            className="inline-flex min-h-10 items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700"
          >
            New encounter
          </Link>
        }
      />

      {isLoading ? (
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="h-28 animate-pulse rounded-xl border border-slate-200 bg-white"
            />
          ))}
        </div>
      ) : null}

      {error ? (
        <section className="mt-8 rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          {error}
        </section>
      ) : null}

      {!isLoading && dashboard ? (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            {[
              { label: "Draft encounters", value: dashboard.draft_count },
              { label: "Completed encounters", value: dashboard.completed_count },
              { label: "Total encounters", value: dashboard.encounters.length },
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

          <section className="mt-8 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-6 py-4">
              <h2 className="font-semibold text-slate-950">Recent encounters</h2>
            </div>

            {dashboard.encounters.length === 0 ? (
              <div className="px-6 py-10 text-center">
                <p className="text-sm text-slate-600">
                  No encounters yet. Start by creating a new encounter.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-200">
                {dashboard.encounters.map((encounter) => (
                  <div
                    key={encounter.id}
                    className="flex flex-col gap-4 px-6 py-5 lg:flex-row lg:items-center lg:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="font-semibold text-slate-950">{encounter.patient_name}</h3>
                        <StatusBadge
                          label={encounter.status === "draft" ? "Draft" : "Completed"}
                          status={encounter.status === "draft" ? "warning" : "success"}
                        />
                      </div>
                      <p className="mt-2 text-sm text-slate-600">
                        Template: {encounter.template_name}
                      </p>
                      <p className="mt-1 text-sm text-slate-500">
                        Encounter date: {formatDateTime(encounter.encounter_date)}
                      </p>
                      <p className="mt-1 text-sm text-slate-500">
                        Last updated: {formatDateTime(encounter.last_updated_at)}
                      </p>
                    </div>

                    <Link
                      href={`/provider/encounters/${encounter.id}`}
                      className="inline-flex min-h-10 items-center justify-center rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-50"
                    >
                      Open encounter
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
