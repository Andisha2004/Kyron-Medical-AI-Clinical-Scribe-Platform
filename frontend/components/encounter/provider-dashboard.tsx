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

  const draftEncounters =
    dashboard?.encounters.filter((encounter) => encounter.status === "draft") ?? [];
  const completedEncounters =
    dashboard?.encounters.filter((encounter) => encounter.status === "completed") ?? [];

  return (
    <div>
      <PageHeader
        title="Provider dashboard"
        description={
          dashboard
            ? `Welcome, ${dashboard.provider_name}. Continue drafts, start new visits, and review completed encounters.`
            : "Continue drafts, start new visits, and review completed encounters."
        }
        actions={
          <Link
            href="/provider/encounters/new"
            data-testid="new-encounter-link"
            className="inline-flex min-h-10 items-center justify-center rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold !text-white shadow-sm hover:bg-slate-700"
          >
            New encounter
          </Link>
        }
      />

      {isLoading ? (
        <div className="mt-8 grid gap-4 sm:grid-cols-3" aria-live="polite" aria-busy="true">
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
          data-testid="provider-dashboard-error"
        >
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
                className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
              >
                <p className="text-sm font-medium text-slate-600">{card.label}</p>
                <p className="mt-3 text-3xl font-bold text-slate-950">{card.value}</p>
              </article>
            ))}
          </div>

          <div className="mt-8 grid gap-6 xl:grid-cols-[1.45fr_0.95fr]">
            <section
              className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm"
              data-testid="provider-encounter-list"
            >
              <div className="border-b border-slate-200 px-6 py-4">
                <h2 className="font-semibold text-slate-950">Continue documentation</h2>
                <p className="mt-1 text-sm text-slate-600">
                  Draft encounters stay editable until you save a version and finalize the note.
                </p>
              </div>

              {draftEncounters.length === 0 ? (
                <div
                  className="px-6 py-10"
                  role="status"
                  aria-live="polite"
                  data-testid="provider-empty-state"
                >
                  <p className="text-sm font-medium text-slate-900">
                    No draft encounters right now.
                  </p>
                  <p className="mt-2 text-sm text-slate-600">
                    Start a new encounter to capture the transcript, add observations, review the
                    SOAP note, and save a formal note version when you are ready.
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
                        data-testid={`open-encounter-${encounter.id}`}
                        className="inline-flex min-h-10 items-center justify-center rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-slate-50"
                      >
                        Resume encounter
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <div className="space-y-6">
              <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="font-semibold text-slate-950">Recommended workflow</h2>
                <ol className="mt-4 space-y-3 text-sm text-slate-600">
                  <li>1. Start a new encounter and confirm the patient and template.</li>
                  <li>2. Capture the visit with transcript and clinical observations.</li>
                  <li>3. Generate or write the SOAP note, then review every section.</li>
                  <li>4. Confirm ICD-10 codes, save a version, and finalize when ready.</li>
                </ol>
              </section>

              <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="font-semibold text-slate-950">What happens next</h2>
                <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-medium text-slate-900">New encounter</p>
                  <p className="mt-1 text-sm text-slate-600">
                    Create the encounter first, then move into transcript capture, SOAP drafting,
                    coding, and final review.
                  </p>
                </div>
                <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-medium text-slate-900">Draft encounter</p>
                  <p className="mt-1 text-sm text-slate-600">
                    Drafts autosave as you work. A permanent checkpoint is created only when you
                    press Save note version.
                  </p>
                </div>
              </section>
            </div>
          </div>

          <section className="mt-8 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-6 py-4">
              <h2 className="font-semibold text-slate-950">Recently completed</h2>
              <p className="mt-1 text-sm text-slate-600">
                Review finished documentation and prior patient history without reopening the full
                drafting flow.
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
                {completedEncounters.slice(0, 5).map((encounter) => (
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
        </>
      ) : null}
    </div>
  );
}
