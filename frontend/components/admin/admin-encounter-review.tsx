"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/page-header";
import { ApiError } from "@/lib/api";
import { getEncounterDetail } from "@/lib/encounters";
import { getNoteVersions } from "@/lib/notes";
import type { EncounterDetailResponse } from "@/types/encounter";
import type { NoteVersion } from "@/types/note";

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

interface AdminEncounterReviewProps {
  encounterId: string;
}

export function AdminEncounterReview({ encounterId }: AdminEncounterReviewProps) {
  const [encounter, setEncounter] = useState<EncounterDetailResponse | null>(null);
  const [versions, setVersions] = useState<NoteVersion[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const encounterResponse = await getEncounterDetail(encounterId);
        if (!isMounted) {
          return;
        }
        setEncounter(encounterResponse);
        if (encounterResponse.note_id) {
          const versionResponse = await getNoteVersions(encounterResponse.note_id);
          if (isMounted) {
            setVersions(versionResponse);
          }
        } else {
          setVersions([]);
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
          setErrorMessage("Unable to load encounter.");
        }
      }
    }

    void load();
    return () => {
      isMounted = false;
    };
  }, [encounterId]);

  if (!encounter) {
    return (
      <div>
        <PageHeader
          title="Read-only encounter review"
          description="Administrators can inspect the encounter and saved note versions."
        />
        <div className="mt-6 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
          {errorMessage || "Loading encounter..."}
        </div>
      </div>
    );
  }

  const latestVersion = versions[0] ?? null;

  return (
    <div>
      <PageHeader
        title={`${encounter.patient.first_name} ${encounter.patient.last_name}`}
        description={`Read-only admin review • Encounter ${formatDateTime(encounter.encounter_date)}`}
      />

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-slate-950">Encounter details</h2>
          <div className="mt-4 space-y-3 text-sm text-slate-700">
            <p>
              <span className="font-semibold text-slate-900">Patient:</span>{" "}
              {encounter.patient.first_name} {encounter.patient.last_name}
            </p>
            <p>
              <span className="font-semibold text-slate-900">Date of birth:</span>{" "}
              {encounter.patient.date_of_birth}
            </p>
            <p>
              <span className="font-semibold text-slate-900">Template:</span>{" "}
              {encounter.template.name}
            </p>
            <p>
              <span className="font-semibold text-slate-900">Status:</span>{" "}
              <span className="capitalize">{encounter.status}</span>
            </p>
          </div>

          <div className="mt-6">
            <p className="text-sm font-semibold text-slate-800">Transcript</p>
            <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm whitespace-pre-wrap text-slate-700">
              {encounter.draft?.transcript || "No transcript available."}
            </div>
          </div>

          <div className="mt-4">
            <p className="text-sm font-semibold text-slate-800">Observations</p>
            <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm whitespace-pre-wrap text-slate-700">
              {encounter.draft?.observations || "No observations available."}
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-slate-950">Saved note versions</h2>
          {latestVersion ? (
            <div className="mt-4 space-y-4">
              <p className="text-sm text-slate-600">
                Showing latest version {latestVersion.version_number} saved{" "}
                {formatDateTime(latestVersion.saved_at)}.
              </p>
              {[
                ["Subjective", latestVersion.subjective],
                ["Objective", latestVersion.objective],
                ["Assessment", latestVersion.assessment],
                ["Plan", latestVersion.plan],
              ].map(([label, value]) => (
                <div key={label}>
                  <p className="text-sm font-semibold text-slate-800">{label}</p>
                  <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm whitespace-pre-wrap text-slate-700">
                    {value || "No content saved for this section."}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-600">No saved note versions yet.</p>
          )}
        </section>
      </div>
    </div>
  );
}
