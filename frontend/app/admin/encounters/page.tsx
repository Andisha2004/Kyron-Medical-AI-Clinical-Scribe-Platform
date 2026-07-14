"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { ApiError } from "@/lib/api";
import { getAdminEncounters, getAdminProviders } from "@/lib/admin";
import type { AdminEncounterListResponse, AdminProviderSummary } from "@/types/admin";

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function AdminEncountersPage() {
  const [providers, setProviders] = useState<AdminProviderSummary[]>([]);
  const [encounters, setEncounters] = useState<AdminEncounterListResponse | null>(null);
  const [providerId, setProviderId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [page, setPage] = useState(1);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    void getAdminProviders()
      .then(setProviders)
      .catch(() => setProviders([]));
  }, []);

  useEffect(() => {
    void getAdminEncounters({
      provider_id: providerId || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      page,
      page_size: 10,
    })
      .then(setEncounters)
      .catch((error: unknown) => {
        if (error instanceof ApiError) {
          setErrorMessage(error.message);
        } else if (error instanceof Error) {
          setErrorMessage(error.message);
        } else {
          setErrorMessage("Unable to load encounters.");
        }
      });
  }, [providerId, startDate, endDate, page]);

  const totalPages = encounters
    ? Math.max(1, Math.ceil(encounters.total / encounters.page_size))
    : 1;

  return (
    <div>
      <PageHeader
        title="Manage encounters"
        description="Review encounter activity and processing status across providers."
      />

      {errorMessage ? (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      ) : null}

      <section className="mt-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="grid gap-4 md:grid-cols-4">
          <select
            value={providerId}
            onChange={(event) => {
              setProviderId(event.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
          >
            <option value="">All providers</option>
            {providers.map((provider) => (
              <option key={provider.id} value={provider.id}>
                {provider.first_name} {provider.last_name}
              </option>
            ))}
          </select>
          <input
            type="date"
            value={startDate}
            onChange={(event) => {
              setStartDate(event.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
          />
          <input
            type="date"
            value={endDate}
            onChange={(event) => {
              setEndDate(event.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
          />
          <Button
            variant="secondary"
            onClick={() => {
              setProviderId("");
              setStartDate("");
              setEndDate("");
              setPage(1);
            }}
          >
            Clear filters
          </Button>
        </div>

        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="text-left text-slate-500">
              <tr>
                <th className="pb-3 font-medium">Patient</th>
                <th className="pb-3 font-medium">Provider</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Template</th>
                <th className="pb-3 font-medium">Encounter date</th>
                <th className="pb-3 font-medium">Open</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {encounters?.items.map((encounter) => (
                <tr key={encounter.id}>
                  <td className="py-3 font-medium text-slate-900">{encounter.patient_name}</td>
                  <td className="py-3 text-slate-700">{encounter.provider_name}</td>
                  <td className="py-3 text-slate-700 capitalize">{encounter.status}</td>
                  <td className="py-3 text-slate-700">{encounter.template_name}</td>
                  <td className="py-3 text-slate-700">
                    {formatDateTime(encounter.encounter_date)}
                  </td>
                  <td className="py-3">
                    <Link
                      className="text-slate-900 underline"
                      href={`/admin/encounters/${encounter.id}`}
                    >
                      Read-only view
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 flex items-center justify-between text-sm text-slate-600">
          <p>Total results: {encounters?.total ?? 0}</p>
          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </Button>
            <span>
              Page {page} of {totalPages}
            </span>
            <Button
              variant="secondary"
              disabled={page >= totalPages}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
