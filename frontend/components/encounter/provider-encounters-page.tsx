"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError } from "@/lib/api";
import { getProviderDashboard } from "@/lib/encounters";
import type { ProviderDashboardResponse } from "@/types/encounter";

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function ProviderEncountersPage() {
  const [dashboard, setDashboard] = useState<ProviderDashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadEncounters() {
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
          setError("Unable to load encounters.");
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadEncounters();

    return () => {
      isMounted = false;
    };
  }, []);

  const draftEncounters =
    dashboard?.encounters.filter((encounter) => encounter.status === "draft") ?? [];
  const completedEncounters =
    dashboard?.encounters.filter((encounter) => encounter.status === "completed") ?? [];

  return (
    <div>
      <PageHeader
        title="Encounters"
        description="Move through the provider workflow: continue drafts, review completed notes, or start a new encounter."
        actions={
          <Link
            href="/provider/encounters/new"
            className="inline-flex min-h-10 items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold !text-white shadow-sm hover:bg-slate-700"
          >
            New encounter
          </Link>
        }
      />

      {isLoading ? (
        <div className="mt-8 space-y-4" aria-live="polite" aria-busy="true">
          {[1, 2, 3].map((item) => (
            <div
              key={item}
              className="h-28 animate-pulse rounded-lg border border-slate-200 bg-white"
            />
          ))}
        </div>
      ) : null}

      {error ? (
        <section
          className="mt-8 rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
          role="alert"
        >
          {error}
        </section>
      ) : null}

      {!isLoading && dashboard ? (
        <div className="mt-8 space-y-6">
          <section className="rounded-lg border border-slate-200 bg-slate-50 p-5">
            <h2 className="font-semibold text-slate-950">Encounter workflow</h2>
            <p className="mt-2 text-sm text-slate-600">
              Draft encounters are where you capture the transcript, add observations, generate or
              edit the SOAP note, confirm ICD-10 codes, and save versions before finalizing.
            </p>
          </section>

          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-6 py-4">
              <h2 className="font-semibold text-slate-950">Draft encounters</h2>
              <p className="mt-1 text-sm text-slate-600">
                {draftEncounters.length} draft{draftEncounters.length === 1 ? "" : "s"} ready to
                continue for {dashboard.provider_name}.
              </p>
            </div>

            {draftEncounters.length === 0 ? (
              <div className="px-6 py-10 text-center">
                <p className="text-sm text-slate-600">
                  No drafts are open right now. Start a new encounter when the next visit begins.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-200">
                {draftEncounters.map((encounter) => (
                  <div
                    key={encounter.id}
                    className="flex flex-col gap-4 px-6 py-5 lg:flex-row lg:items-center lg:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="font-semibold text-slate-950">{encounter.patient_name}</h3>
                        <StatusBadge label="Draft" status="warning" />
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
                      className="inline-flex min-h-10 items-center justify-center rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-50"
                    >
                      Resume encounter
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-6 py-4">
              <h2 className="font-semibold text-slate-950">Completed encounters</h2>
              <p className="mt-1 text-sm text-slate-600">
                Review saved work, prior patient history, and finished documentation.
              </p>
            </div>

            {completedEncounters.length === 0 ? (
              <div className="px-6 py-10 text-center">
                <p className="text-sm text-slate-600">
                  Completed encounters will appear here after you save and finish them.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-200">
                {completedEncounters.map((encounter) => (
                  <div
                    key={encounter.id}
                    className="flex flex-col gap-4 px-6 py-5 lg:flex-row lg:items-center lg:justify-between"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <h3 className="font-semibold text-slate-950">{encounter.patient_name}</h3>
                        <StatusBadge label="Completed" status="success" />
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
                      className="inline-flex min-h-10 items-center justify-center rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-50"
                    >
                      Review encounter
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}
