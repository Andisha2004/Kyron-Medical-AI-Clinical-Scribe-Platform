"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { ApiError } from "@/lib/api";
import { publicEnv } from "@/lib/env";
import { getEncounterDetail, saveEncounterNote, updateEncounterDraft } from "@/lib/encounters";
import { getNoteVersions } from "@/lib/notes";
import { streamJsonEvents } from "@/lib/stream";
import { getActiveTemplates } from "@/lib/templates";
import type {
  DraftState,
  EncounterDetailResponse,
  EncounterDraftResponse,
} from "@/types/encounter";
import type { GenerationEventDataMap } from "@/types/generation";
import type { NoteVersion } from "@/types/note";
import type { TemplateSummary } from "@/types/template";

type SaveState = "loading" | "idle" | "saving" | "saved" | "error" | "conflict";

const emptyDraftState: DraftState = {
  transcript: "",
  observations: "",
  subjective: "",
  objective: "",
  assessment: "",
  plan: "",
  selected_icd10_codes: [],
};

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function draftFromResponse(draft: EncounterDraftResponse | null | undefined): DraftState {
  if (!draft) {
    return emptyDraftState;
  }

  return {
    transcript: draft.transcript ?? "",
    observations: draft.observations ?? "",
    subjective: draft.subjective ?? "",
    objective: draft.objective ?? "",
    assessment: draft.assessment ?? "",
    plan: draft.plan ?? "",
    selected_icd10_codes: draft.selected_icd10_codes ?? [],
  };
}

function splitLines(value: string | null | undefined): string[] {
  if (!value) {
    return [];
  }

  return value.split("\n");
}

function getChangedSegments(
  previousValue: string | null | undefined,
  currentValue: string | null | undefined,
): {
  removed: string;
  added: string;
  changed: boolean;
} {
  const previousLines = splitLines(previousValue);
  const currentLines = splitLines(currentValue);

  let prefixLength = 0;
  while (
    prefixLength < previousLines.length &&
    prefixLength < currentLines.length &&
    previousLines[prefixLength] === currentLines[prefixLength]
  ) {
    prefixLength += 1;
  }

  let previousSuffixLength = previousLines.length - 1;
  let currentSuffixLength = currentLines.length - 1;

  while (
    previousSuffixLength >= prefixLength &&
    currentSuffixLength >= prefixLength &&
    previousLines[previousSuffixLength] === currentLines[currentSuffixLength]
  ) {
    previousSuffixLength -= 1;
    currentSuffixLength -= 1;
  }

  const removed = previousLines.slice(prefixLength, previousSuffixLength + 1).join("\n");
  const added = currentLines.slice(prefixLength, currentSuffixLength + 1).join("\n");

  return {
    removed,
    added,
    changed: removed !== added,
  };
}

function statusLabel(
  state: SaveState,
  isDirty: boolean,
): { label: string; status: "neutral" | "success" | "warning" | "danger" } {
  if (state === "loading") {
    return { label: "Loading", status: "neutral" };
  }

  if (state === "saving") {
    return { label: "Saving", status: "warning" };
  }

  if (state === "saved") {
    return { label: "Saved", status: "success" };
  }

  if (state === "error") {
    return { label: "Save failed", status: "danger" };
  }

  if (state === "conflict") {
    return { label: "Conflict", status: "danger" };
  }

  if (isDirty) {
    return { label: "Unsaved changes", status: "warning" };
  }

  return { label: "Draft", status: "neutral" };
}

interface EncounterWorkspaceProps {
  encounterId: string;
}

export function EncounterWorkspace({ encounterId }: EncounterWorkspaceProps) {
  const searchParams = useSearchParams();
  const [encounter, setEncounter] = useState<EncounterDetailResponse | null>(null);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [draft, setDraft] = useState<DraftState>(emptyDraftState);
  const [baseRevision, setBaseRevision] = useState<number | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [saveState, setSaveState] = useState<SaveState>("loading");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [conflictDraft, setConflictDraft] = useState<EncounterDraftResponse | null>(null);
  const [isSavingNote, setIsSavingNote] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatusMessage, setGenerationStatusMessage] = useState<string | null>(null);
  const [generationWarnings, setGenerationWarnings] = useState<string[]>([]);
  const [missingInformation, setMissingInformation] = useState<string[]>([]);
  const [versions, setVersions] = useState<NoteVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<NoteVersion | null>(null);
  const [comparisonVersionId, setComparisonVersionId] = useState<string>("");
  const hasLoadedInitialData = useRef(false);
  const lastSaveIdempotencyKeyRef = useRef<string | null>(null);

  const flashMessage = useMemo(() => {
    if (searchParams.get("created") !== "1") {
      return null;
    }

    if (searchParams.get("priorHistory") === "true") {
      return `Encounter created. Prior patient history was found (${searchParams.get("priorCount") || "0"} previous encounter${searchParams.get("priorCount") === "1" ? "" : "s"}).`;
    }

    if (searchParams.get("reused") === "true") {
      return "Encounter created. Existing patient record reused.";
    }

    return "Encounter created. New patient record and empty draft are ready.";
  }, [searchParams]);

  useEffect(() => {
    let isMounted = true;

    async function loadWorkspace() {
      try {
        const [encounterResponse, templateResponse] = await Promise.all([
          getEncounterDetail(encounterId),
          getActiveTemplates(),
        ]);

        if (!isMounted) {
          return;
        }

        setEncounter(encounterResponse);
        setTemplates(templateResponse);
        setDraft(draftFromResponse(encounterResponse.draft));
        setBaseRevision(encounterResponse.draft?.draft_revision ?? null);
        if (encounterResponse.note_id) {
          const versionResponse = await getNoteVersions(encounterResponse.note_id);
          if (isMounted) {
            setVersions(versionResponse);
            setSelectedVersion(versionResponse[0] ?? null);
            setComparisonVersionId(versionResponse[1]?.id ?? "");
          }
        } else {
          setVersions([]);
          setSelectedVersion(null);
          setComparisonVersionId("");
        }
        setIsDirty(false);
        setSaveState("idle");
        setErrorMessage(null);
        setConflictDraft(null);
        hasLoadedInitialData.current = true;
      } catch (error) {
        if (!isMounted) {
          return;
        }

        if (error instanceof ApiError) {
          if (error.status === 404) {
            setErrorMessage("The requested encounter could not be found.");
          } else if (error.status === 403) {
            setErrorMessage("You do not have access to this encounter.");
          } else {
            setErrorMessage(error.message);
          }
        } else if (error instanceof Error) {
          setErrorMessage(error.message);
        } else {
          setErrorMessage("Unable to load the encounter workspace.");
        }
        setSaveState("error");
      }
    }

    void loadWorkspace();

    return () => {
      isMounted = false;
    };
  }, [encounterId]);

  useEffect(() => {
    if (!hasLoadedInitialData.current || !isDirty || saveState === "conflict") {
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      setSaveState("saving");
      try {
        const response = await updateEncounterDraft(encounterId, {
          base_revision: baseRevision,
          ...draft,
        });
        setBaseRevision(response.draft_revision);
        setDraft(draftFromResponse(response));
        setIsDirty(false);
        setSaveState("saved");
        setConflictDraft(null);
        setEncounter((current) =>
          current
            ? {
                ...current,
                draft: response,
              }
            : current,
        );
      } catch (error) {
        if (error instanceof ApiError && error.status === 409) {
          const latestDraft = error.body?.errors?.latest_draft as
            EncounterDraftResponse | undefined;
          if (latestDraft) {
            setConflictDraft(latestDraft);
          }
          setSaveState("conflict");
          return;
        }

        setSaveState("error");
      }
    }, 1000);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [baseRevision, draft, encounterId, isDirty, saveState]);

  async function refreshEncounterDetails() {
    const refreshedEncounter = await getEncounterDetail(encounterId);
    setEncounter(refreshedEncounter);
    setDraft(draftFromResponse(refreshedEncounter.draft));
    setBaseRevision(refreshedEncounter.draft?.draft_revision ?? null);
    if (refreshedEncounter.note_id) {
      const versionResponse = await getNoteVersions(refreshedEncounter.note_id);
      setVersions(versionResponse);
      let nextSelectedVersion: NoteVersion | null = null;
      setSelectedVersion((current) => {
        nextSelectedVersion = current
          ? (versionResponse.find((version) => version.id === current.id) ??
            versionResponse[0] ??
            null)
          : (versionResponse[0] ?? null);
        return nextSelectedVersion;
      });
      setComparisonVersionId((current) => {
        if (!nextSelectedVersion) {
          return "";
        }

        if (current && versionResponse.some((version) => version.id === current)) {
          return current;
        }

        return versionResponse.find((version) => version.id !== nextSelectedVersion?.id)?.id ?? "";
      });
    } else {
      setVersions([]);
      setSelectedVersion(null);
      setComparisonVersionId("");
    }
    setIsDirty(false);
    setSaveState("idle");
    setConflictDraft(null);
  }

  useEffect(() => {
    if (!selectedVersion) {
      setComparisonVersionId("");
      return;
    }

    setComparisonVersionId((current) => {
      if (
        current &&
        current !== selectedVersion.id &&
        versions.some((version) => version.id === current)
      ) {
        return current;
      }

      return versions.find((version) => version.id !== selectedVersion.id)?.id ?? "";
    });
  }, [selectedVersion, versions]);

  function updateField(field: keyof DraftState, value: string | Array<Record<string, string>>) {
    setDraft((current) => ({
      ...current,
      [field]: value,
    }));
    lastSaveIdempotencyKeyRef.current = null;
    setIsDirty(true);
    setSaveState("idle");
  }

  async function handleSaveNote() {
    setIsSavingNote(true);
    setErrorMessage(null);
    const idempotencyKey = lastSaveIdempotencyKeyRef.current ?? crypto.randomUUID();
    lastSaveIdempotencyKeyRef.current = idempotencyKey;
    try {
      await saveEncounterNote(encounterId, {
        subjective: draft.subjective,
        objective: draft.objective,
        assessment: draft.assessment,
        plan: draft.plan,
        icd10_codes: draft.selected_icd10_codes,
        idempotency_key: idempotencyKey,
        generation_metadata: { source: "phase6_workspace_manual_save" },
      });
      await refreshEncounterDetails();
      lastSaveIdempotencyKeyRef.current = null;
    } catch (error) {
      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to save the note version.");
      }
    } finally {
      setIsSavingNote(false);
    }
  }

  async function handleGenerateNote() {
    setIsGenerating(true);
    setErrorMessage(null);
    setGenerationWarnings([]);
    setMissingInformation([]);
    setGenerationStatusMessage("Starting note generation...");

    try {
      await streamJsonEvents<{ [key: string]: unknown }>(
        `${publicEnv.apiBaseUrl}/api/encounters/${encounterId}/generate`,
        {
          method: "POST",
          credentials: "include",
          headers: {
            Accept: "text/event-stream",
          },
        },
        (streamEvent) => {
          if (streamEvent.event === "generation_started") {
            lastSaveIdempotencyKeyRef.current = null;
            setDraft((current) => ({
              ...current,
              subjective: "",
              objective: "",
              assessment: "",
              plan: "",
              selected_icd10_codes: [],
            }));
            setGenerationStatusMessage("Generating SOAP note...");
            return;
          }

          if (streamEvent.event === "section_delta") {
            const data = streamEvent.data as unknown as GenerationEventDataMap["section_delta"];
            setDraft((current) => ({
              ...current,
              [data.section]: `${current[data.section]}${data.text}`,
            }));
            setGenerationStatusMessage(`Updating ${data.section}...`);
            return;
          }

          if (streamEvent.event === "assessment_code") {
            const data = streamEvent.data as unknown as GenerationEventDataMap["assessment_code"];
            setDraft((current) => ({
              ...current,
              selected_icd10_codes: [
                ...current.selected_icd10_codes,
                {
                  code: data.code || "",
                  description: data.description || data.diagnosis,
                  diagnosis: data.diagnosis,
                },
              ],
            }));
            return;
          }

          if (streamEvent.event === "warning") {
            const data = streamEvent.data as unknown as GenerationEventDataMap["warning"];
            setGenerationWarnings((current) => [...current, data.message]);
            return;
          }

          if (streamEvent.event === "draft_saved") {
            const data = streamEvent.data as unknown as GenerationEventDataMap["draft_saved"];
            setBaseRevision(data.draft_revision);
            setIsDirty(false);
            setSaveState("saved");
            setGenerationStatusMessage("Draft saved.");
            return;
          }

          if (streamEvent.event === "generation_complete") {
            const data =
              streamEvent.data as unknown as GenerationEventDataMap["generation_complete"];
            setMissingInformation(data.missing_information);
            setGenerationWarnings((current) => [...current, ...data.warnings]);
            setGenerationStatusMessage("Generation complete.");
            return;
          }

          if (streamEvent.event === "generation_error") {
            const data = streamEvent.data as unknown as GenerationEventDataMap["generation_error"];
            setErrorMessage(data.message);
            setGenerationStatusMessage("Generation failed.");
          }
        },
      );
    } catch (error) {
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to generate the SOAP note.");
      }
      setGenerationStatusMessage("Generation failed.");
    } finally {
      setIsGenerating(false);
    }
  }

  const persistenceStatus = statusLabel(saveState, isDirty);
  const soapSections: Array<{
    field: keyof Pick<DraftState, "subjective" | "objective" | "assessment" | "plan">;
    label: string;
    rows: number;
  }> = [
    { field: "subjective", label: "Subjective", rows: 5 },
    { field: "objective", label: "Objective", rows: 5 },
    { field: "assessment", label: "Assessment", rows: 5 },
    { field: "plan", label: "Plan", rows: 5 },
  ];

  function renderVersionAuthor(version: NoteVersion): string {
    if (version.saved_by_user.first_name || version.saved_by_user.last_name) {
      return `${version.saved_by_user.first_name ?? ""} ${version.saved_by_user.last_name ?? ""}`.trim();
    }
    return version.saved_by_user.email;
  }

  const comparisonVersion =
    comparisonVersionId && selectedVersion
      ? (versions.find((version) => version.id === comparisonVersionId) ?? null)
      : null;

  const comparisonSections = selectedVersion
    ? [
        {
          label: "Subjective",
          ...getChangedSegments(comparisonVersion?.subjective, selectedVersion.subjective),
        },
        {
          label: "Objective",
          ...getChangedSegments(comparisonVersion?.objective, selectedVersion.objective),
        },
        {
          label: "Assessment",
          ...getChangedSegments(comparisonVersion?.assessment, selectedVersion.assessment),
        },
        {
          label: "Plan",
          ...getChangedSegments(comparisonVersion?.plan, selectedVersion.plan),
        },
      ]
    : [];

  if (!encounter && saveState === "loading") {
    return (
      <div className="space-y-6">
        <div className="h-10 w-64 animate-pulse rounded bg-slate-200" />
        <div className="grid gap-6 xl:grid-cols-2">
          <div className="h-80 animate-pulse rounded-xl bg-slate-200" />
          <div className="h-80 animate-pulse rounded-xl bg-slate-200" />
        </div>
      </div>
    );
  }

  if (!encounter) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
        {errorMessage || "Unable to open the encounter workspace."}
      </section>
    );
  }

  return (
    <div>
      <PageHeader
        title={`${encounter.patient.first_name} ${encounter.patient.last_name}`}
        description={`DOB ${encounter.patient.date_of_birth} • Encounter ${formatDateTime(encounter.encounter_date)}`}
        actions={<StatusBadge label={persistenceStatus.label} status={persistenceStatus.status} />}
      />

      {flashMessage ? (
        <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {flashMessage}
        </div>
      ) : null}

      {errorMessage ? (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      ) : null}

      {generationStatusMessage ? (
        <div className="mt-6 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
          {generationStatusMessage}
        </div>
      ) : null}

      {missingInformation.length > 0 ? (
        <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Missing information: {missingInformation.join(" ")}
        </div>
      ) : null}

      {generationWarnings.length > 0 ? (
        <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Warnings: {generationWarnings.join(" ")}
        </div>
      ) : null}

      {saveState === "conflict" ? (
        <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-800">
          <p className="font-semibold">Another saved draft version was detected.</p>
          <p className="mt-1">
            Your local edits are still here. You can reload the latest saved draft or keep your
            current local content and continue editing.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button
              variant="secondary"
              onClick={() => {
                if (!conflictDraft) {
                  return;
                }
                setDraft(draftFromResponse(conflictDraft));
                setBaseRevision(conflictDraft.draft_revision);
                setIsDirty(false);
                setSaveState("idle");
                setConflictDraft(null);
              }}
            >
              Reload latest saved draft
            </Button>
            <Button
              onClick={() => {
                if (conflictDraft) {
                  setBaseRevision(conflictDraft.draft_revision);
                }
                setSaveState("idle");
              }}
            >
              Keep local changes
            </Button>
          </div>
        </div>
      ) : null}

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.05fr_1fr]">
        <section className="space-y-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-semibold text-slate-950">Encounter details</h2>
              <StatusBadge
                label={encounter.status === "draft" ? "Draft" : "Completed"}
                status={encounter.status === "draft" ? "warning" : "success"}
              />
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-semibold text-slate-800">Template</label>
                <select
                  value={encounter.template_id}
                  disabled
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 disabled:bg-slate-100"
                >
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-800">Persistence status</p>
                <p className="mt-2 text-sm text-slate-600">
                  Draft revision {baseRevision ?? encounter.draft?.draft_revision ?? 1}
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="font-semibold text-slate-950">Transcript</h2>
            <textarea
              rows={10}
              value={draft.transcript}
              onChange={(event) => updateField("transcript", event.target.value)}
              className="mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
              placeholder="Paste or type the encounter transcript here."
            />

            <h3 className="mt-6 font-semibold text-slate-950">Clinical observations</h3>
            <textarea
              rows={6}
              value={draft.observations}
              onChange={(event) => updateField("observations", event.target.value)}
              className="mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
              placeholder="Add non-transcript clinical observations here."
            />
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="font-semibold text-slate-950">Dictation and voice controls</h2>
            <p className="mt-3 text-sm text-slate-600">
              Live dictation, ICD-10 search, and voice editing will be connected in the next phases.
              This workspace already persists transcript and SOAP edits safely.
            </p>
          </div>
        </section>

        <section className="space-y-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="font-semibold text-slate-950">SOAP note</h2>
              <div className="flex flex-wrap gap-3">
                <Button
                  variant="secondary"
                  onClick={() => void handleGenerateNote()}
                  disabled={isGenerating}
                >
                  {isGenerating ? "Generating..." : "Generate SOAP note"}
                </Button>
                <Button onClick={() => void handleSaveNote()} disabled={isSavingNote}>
                  {isSavingNote ? "Saving note..." : "Save note version"}
                </Button>
              </div>
            </div>

            {soapSections.map(({ field, label, rows }) => (
              <div key={field} className="mt-5">
                <label className="block text-sm font-semibold text-slate-800">{label}</label>
                <textarea
                  rows={rows}
                  value={draft[field]}
                  onChange={(event) => updateField(field, event.target.value)}
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                  placeholder={`Enter ${label.toLowerCase()} content.`}
                />
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="font-semibold text-slate-950">Version history</h2>
            {versions.length === 0 ? (
              <p className="mt-3 text-sm text-slate-600">
                No note versions saved yet. Draft autosave is active, but formal note versioning
                begins when you press Save note version.
              </p>
            ) : (
              <div className="mt-4 space-y-4">
                <div className="space-y-3">
                  {versions.map((version) => (
                    <button
                      key={version.id}
                      type="button"
                      onClick={() => {
                        setSelectedVersion(version);
                      }}
                      className={`block w-full rounded-lg border px-4 py-3 text-left ${
                        selectedVersion?.id === version.id
                          ? "border-slate-900 bg-slate-100"
                          : "border-slate-200 bg-slate-50"
                      }`}
                    >
                      <p className="text-sm font-semibold text-slate-900">
                        Version {version.version_number}
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        Saved {formatDateTime(version.saved_at)} by {renderVersionAuthor(version)}
                      </p>
                    </button>
                  ))}
                </div>

                {selectedVersion ? (
                  <div className="rounded-lg border border-slate-200 bg-white p-4">
                    <h3 className="font-semibold text-slate-950">
                      Version {selectedVersion.version_number} details
                    </h3>
                    <p className="mt-1 text-sm text-slate-600">
                      Saved {formatDateTime(selectedVersion.saved_at)} by{" "}
                      {renderVersionAuthor(selectedVersion)}
                    </p>
                    {[
                      ["Subjective", selectedVersion.subjective],
                      ["Objective", selectedVersion.objective],
                      ["Assessment", selectedVersion.assessment],
                      ["Plan", selectedVersion.plan],
                    ].map(([label, value]) => (
                      <div key={label} className="mt-4">
                        <p className="text-sm font-semibold text-slate-800">{label}</p>
                        <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm whitespace-pre-wrap text-slate-700">
                          {value || "No content saved for this section."}
                        </div>
                      </div>
                    ))}

                    {versions.length > 1 ? (
                      <div className="mt-6 border-t border-slate-200 pt-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <h4 className="text-sm font-semibold text-slate-900">
                              Version comparison
                            </h4>
                            <p className="mt-1 text-sm text-slate-600">
                              Compare this saved version against another version.
                            </p>
                          </div>

                          <div className="min-w-64">
                            <label
                              htmlFor="comparison-version"
                              className="block text-sm font-semibold text-slate-800"
                            >
                              Compare against
                            </label>
                            <select
                              id="comparison-version"
                              value={comparisonVersionId}
                              onChange={(event) => setComparisonVersionId(event.target.value)}
                              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900"
                            >
                              {versions
                                .filter((version) => version.id !== selectedVersion.id)
                                .map((version) => (
                                  <option key={version.id} value={version.id}>
                                    Version {version.version_number} •{" "}
                                    {formatDateTime(version.saved_at)}
                                  </option>
                                ))}
                            </select>
                          </div>
                        </div>

                        {comparisonVersion ? (
                          <div className="mt-4 space-y-4">
                            {comparisonSections.map((section) => (
                              <div
                                key={section.label}
                                className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                              >
                                <p className="text-sm font-semibold text-slate-900">
                                  {section.label}
                                </p>

                                {!section.changed ? (
                                  <p className="mt-2 text-sm text-slate-600">
                                    No changes between these versions for this section.
                                  </p>
                                ) : (
                                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                                    <div>
                                      <p className="text-xs font-semibold tracking-wide text-red-700 uppercase">
                                        Removed
                                      </p>
                                      <div className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm whitespace-pre-wrap text-red-900">
                                        {section.removed || "No removed content."}
                                      </div>
                                    </div>
                                    <div>
                                      <p className="text-xs font-semibold tracking-wide text-emerald-700 uppercase">
                                        Added
                                      </p>
                                      <div className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm whitespace-pre-wrap text-emerald-900">
                                        {section.added || "No added content."}
                                      </div>
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
