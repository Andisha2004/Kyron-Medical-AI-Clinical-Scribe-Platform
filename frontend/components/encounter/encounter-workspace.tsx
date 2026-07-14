"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { DictationPanel } from "@/components/encounter/dictation-panel";
import { VoiceEditPanel } from "@/components/encounter/voice-edit-panel";
import { ApiError } from "@/lib/api";
import { publicEnv } from "@/lib/env";
import { getEncounterDetail, saveEncounterNote, updateEncounterDraft } from "@/lib/encounters";
import { searchIcdCodes } from "@/lib/icd";
import { getNoteVersions } from "@/lib/notes";
import { streamJsonEvents } from "@/lib/stream";
import { getActiveTemplates } from "@/lib/templates";
import type {
  DraftState,
  EncounterDetailResponse,
  EncounterDraftResponse,
} from "@/types/encounter";
import type { GenerationEventDataMap } from "@/types/generation";
import type { IcdSearchResult } from "@/types/icd";
import type { NoteVersion } from "@/types/note";
import type { TemplateSummary } from "@/types/template";

type SaveState = "loading" | "idle" | "saving" | "saved" | "error" | "conflict";

interface SaveRecoverySnapshot {
  encounterId: string;
  draft: DraftState;
  baseRevision: number | null;
  idempotencyKey: string;
  savedAt: string;
}

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

function recoveryStorageKey(encounterId: string): string {
  return `kyron:save-recovery:${encounterId}`;
}

function isDeactivatedApiError(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.status === 403 &&
    error.message.toLowerCase().includes("deactivated")
  );
}

function isExpiredApiError(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.status === 401 &&
    error.message.toLowerCase().includes("expired")
  );
}

interface EncounterWorkspaceProps {
  encounterId: string;
}

export function EncounterWorkspace({ encounterId }: EncounterWorkspaceProps) {
  const router = useRouter();
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
  const [icdQuery, setIcdQuery] = useState("");
  const [icdResults, setIcdResults] = useState<IcdSearchResult[]>([]);
  const [isSearchingIcd, setIsSearchingIcd] = useState(false);
  const [icdSearchError, setIcdSearchError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [accountDeactivated, setAccountDeactivated] = useState(false);
  const [saveRecovery, setSaveRecovery] = useState<SaveRecoverySnapshot | null>(null);
  const [isRetryingRecoveredSave, setIsRetryingRecoveredSave] = useState(false);
  const hasLoadedInitialData = useRef(false);
  const lastSaveIdempotencyKeyRef = useRef<string | null>(null);
  const generationDraftBackupRef = useRef<DraftState | null>(null);
  const generationReceivedContentRef = useRef(false);

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

  function persistSaveRecovery(snapshot: SaveRecoverySnapshot) {
    window.localStorage.setItem(recoveryStorageKey(encounterId), JSON.stringify(snapshot));
    setSaveRecovery(snapshot);
  }

  function clearSaveRecovery() {
    window.localStorage.removeItem(recoveryStorageKey(encounterId));
    setSaveRecovery(null);
  }

  function routeToLoginForRecovery(reason: "expired" | "deactivated") {
    router.replace(
      `/login?next=${encodeURIComponent(`/provider/encounters/${encounterId}`)}&reason=${reason}`,
    );
  }

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
        setSessionExpired(false);
        setAccountDeactivated(false);
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
        const recoveryValue = window.localStorage.getItem(recoveryStorageKey(encounterId));
        if (recoveryValue) {
          try {
            const parsedRecovery = JSON.parse(recoveryValue) as SaveRecoverySnapshot;
            if (parsedRecovery.encounterId === encounterId) {
              setDraft(parsedRecovery.draft);
              setBaseRevision(parsedRecovery.baseRevision);
              lastSaveIdempotencyKeyRef.current = parsedRecovery.idempotencyKey;
              setSaveRecovery(parsedRecovery);
              setIsDirty(true);
              setSaveState("idle");
              setErrorMessage(
                "Your session expired during save. Your latest note state was restored locally. Sign in again and retry the save.",
              );
            }
          } catch {
            window.localStorage.removeItem(recoveryStorageKey(encounterId));
          }
        }
        hasLoadedInitialData.current = true;
      } catch (error) {
        if (!isMounted) {
          return;
        }

        if (error instanceof ApiError) {
          if (isExpiredApiError(error)) {
            setSessionExpired(true);
            setErrorMessage("Your session expired. Sign in again to continue.");
            setSaveState("error");
            return;
          }
          if (isDeactivatedApiError(error)) {
            setAccountDeactivated(true);
            setErrorMessage(
              "Your account has been deactivated. Your current draft remains available locally, but protected actions are blocked.",
            );
            setSaveState("error");
            return;
          }
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
    if (
      !hasLoadedInitialData.current ||
      !isDirty ||
      saveState === "conflict" ||
      sessionExpired ||
      accountDeactivated
    ) {
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
        if (isExpiredApiError(error)) {
          setSessionExpired(true);
          setErrorMessage("Your session expired. Sign in again to continue saving.");
          setSaveState("error");
          return;
        }

        if (isDeactivatedApiError(error)) {
          setAccountDeactivated(true);
          setErrorMessage(
            "Your account has been deactivated. Automatic saving has been stopped, and your current draft remains in this browser.",
          );
          setSaveState("error");
          return;
        }

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
  }, [accountDeactivated, baseRevision, draft, encounterId, isDirty, saveState, sessionExpired]);

  useEffect(() => {
    if (!publicEnv.enableIcdSearch) {
      return;
    }

    const normalizedQuery = icdQuery.trim();
    if (normalizedQuery.length < 2) {
      setIcdResults([]);
      setIsSearchingIcd(false);
      setIcdSearchError(null);
      return;
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(async () => {
      setIsSearchingIcd(true);
      setIcdSearchError(null);

      try {
        const results = await searchIcdCodes(normalizedQuery, {
          signal: controller.signal,
          limit: 8,
        });
        setIcdResults(results);
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiError) {
          setIcdSearchError(error.message);
        } else if (error instanceof Error) {
          setIcdSearchError(error.message);
        } else {
          setIcdSearchError("Unable to search ICD-10 codes.");
        }
        setIcdResults([]);
      } finally {
        if (!controller.signal.aborted) {
          setIsSearchingIcd(false);
        }
      }
    }, 350);

    return () => {
      controller.abort();
      window.clearTimeout(timeoutId);
    };
  }, [icdQuery]);

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
      clearSaveRecovery();
    } catch (error) {
      if (isExpiredApiError(error)) {
        const recoverySnapshot: SaveRecoverySnapshot = {
          encounterId,
          draft,
          baseRevision,
          idempotencyKey,
          savedAt: new Date().toISOString(),
        };
        persistSaveRecovery(recoverySnapshot);
        setSessionExpired(true);
        setErrorMessage(
          "Your session expired. Your work has not been lost. Sign in again to retry the save.",
        );
        routeToLoginForRecovery("expired");
        return;
      }

      if (isDeactivatedApiError(error)) {
        setAccountDeactivated(true);
        setErrorMessage(
          "Your account has been deactivated. Your draft remains visible here, but saving is blocked.",
        );
        return;
      }

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

  async function handleRetryRecoveredSave() {
    if (!saveRecovery) {
      return;
    }

    setIsRetryingRecoveredSave(true);
    setErrorMessage(null);
    try {
      await saveEncounterNote(encounterId, {
        subjective: saveRecovery.draft.subjective,
        objective: saveRecovery.draft.objective,
        assessment: saveRecovery.draft.assessment,
        plan: saveRecovery.draft.plan,
        icd10_codes: saveRecovery.draft.selected_icd10_codes,
        idempotency_key: saveRecovery.idempotencyKey,
        generation_metadata: {
          source: "phase11_recovered_save_retry",
          recovered_at: saveRecovery.savedAt,
        },
      });
      await refreshEncounterDetails();
      lastSaveIdempotencyKeyRef.current = null;
      clearSaveRecovery();
      setSessionExpired(false);
    } catch (error) {
      if (isExpiredApiError(error)) {
        setSessionExpired(true);
        setErrorMessage("Your session is still expired. Sign in again before retrying the save.");
        routeToLoginForRecovery("expired");
        return;
      }
      if (isDeactivatedApiError(error)) {
        setAccountDeactivated(true);
        setErrorMessage("Your account has been deactivated. The recovered note cannot be saved.");
        return;
      }
      setErrorMessage(
        error instanceof Error ? error.message : "Unable to retry the recovered save.",
      );
    } finally {
      setIsRetryingRecoveredSave(false);
    }
  }

  async function handleGenerateNote() {
    if (accountDeactivated) {
      setErrorMessage("Your account has been deactivated. Note generation is unavailable.");
      return;
    }

    setIsGenerating(true);
    setErrorMessage(null);
    setGenerationWarnings([]);
    setMissingInformation([]);
    setGenerationStatusMessage("Starting note generation...");
    generationDraftBackupRef.current = {
      transcript: draft.transcript,
      observations: draft.observations,
      subjective: draft.subjective,
      objective: draft.objective,
      assessment: draft.assessment,
      plan: draft.plan,
      selected_icd10_codes: [...draft.selected_icd10_codes],
    };
    generationReceivedContentRef.current = false;

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
            setGenerationStatusMessage("Generating SOAP note...");
            return;
          }

          if (streamEvent.event === "section_delta") {
            const data = streamEvent.data as unknown as GenerationEventDataMap["section_delta"];
            if (!generationReceivedContentRef.current) {
              generationReceivedContentRef.current = true;
              setDraft((current) => ({
                ...current,
                subjective: "",
                objective: "",
                assessment: "",
                plan: "",
                selected_icd10_codes: [],
              }));
            }
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
            if (generationDraftBackupRef.current) {
              setDraft(generationDraftBackupRef.current);
            }
            setErrorMessage(data.message);
            setGenerationStatusMessage("Generation failed.");
          }
        },
      );
    } catch (error) {
      if (generationDraftBackupRef.current) {
        setDraft(generationDraftBackupRef.current);
      }
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("Unable to generate the SOAP note.");
      }
      setGenerationStatusMessage("Generation failed.");
    } finally {
      generationDraftBackupRef.current = null;
      generationReceivedContentRef.current = false;
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

  function addSelectedIcdCode(result: IcdSearchResult) {
    if (draft.selected_icd10_codes.some((item) => item.code === result.code)) {
      return;
    }

    updateField("selected_icd10_codes", [
      ...draft.selected_icd10_codes,
      {
        code: result.code,
        description: result.description,
      },
    ]);
  }

  function removeSelectedIcdCode(code: string) {
    updateField(
      "selected_icd10_codes",
      draft.selected_icd10_codes.filter((item) => item.code !== code),
    );
  }

  function handleRealtimeDraftApplied(response: {
    draft: EncounterDraftResponse;
    draft_revision: number;
  }) {
    setDraft(draftFromResponse(response.draft));
    setBaseRevision(response.draft_revision);
    setIsDirty(false);
    setSaveState("saved");
    setConflictDraft(null);
    setEncounter((current) =>
      current
        ? {
            ...current,
            draft: response.draft,
          }
        : current,
    );
    setErrorMessage(null);
    setSessionExpired(false);
    setAccountDeactivated(false);
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
      <div className="space-y-6" aria-busy="true">
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
      <section
        className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
        role="alert"
      >
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

      <div className="sr-only" role="status" aria-live="polite" data-testid="workspace-live-status">
        {persistenceStatus.label}. {generationStatusMessage ?? ""}{" "}
        {sessionExpired ? "Session expired." : ""}
        {accountDeactivated ? "Account deactivated." : ""}
      </div>

      {flashMessage ? (
        <div
          className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"
          role="status"
        >
          {flashMessage}
        </div>
      ) : null}

      {errorMessage ? (
        <div
          className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          role="alert"
          data-testid="workspace-error"
        >
          {errorMessage}
        </div>
      ) : null}

      {generationStatusMessage ? (
        <div
          className="mt-6 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800"
          role="status"
          aria-live="polite"
          data-testid="generation-status"
        >
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

      {saveRecovery ? (
        <div className="mt-6 rounded-lg border border-blue-200 bg-blue-50 px-4 py-4 text-sm text-blue-900">
          <p className="font-semibold">Recovered save available</p>
          <p className="mt-1">
            A previous save attempt was interrupted after your session expired. Your latest note
            state was restored locally from {formatDateTime(saveRecovery.savedAt)}.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <Button
              onClick={() => void handleRetryRecoveredSave()}
              disabled={isRetryingRecoveredSave}
            >
              {isRetryingRecoveredSave ? "Retrying save..." : "Retry recovered save"}
            </Button>
            <Button variant="secondary" onClick={clearSaveRecovery}>
              Dismiss recovery copy
            </Button>
          </div>
        </div>
      ) : null}

      {accountDeactivated ? (
        <div className="mt-6 rounded-lg border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-800">
          <p className="font-semibold">Account deactivated</p>
          <p className="mt-1">
            Your provider account was deactivated while this draft was open. Your current text has
            been preserved in this browser, but protected actions such as saving, generating, voice
            editing, and dictation are blocked.
          </p>
          <div className="mt-4">
            <Button variant="secondary" onClick={() => routeToLoginForRecovery("deactivated")}>
              Return to sign in
            </Button>
          </div>
        </div>
      ) : null}

      <div className="mt-8 space-y-6">
        <div
          className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          data-testid="encounter-details-panel"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-semibold text-slate-950">Encounter details</h2>
            <StatusBadge
              label={encounter.status === "draft" ? "Draft" : "Completed"}
              status={encounter.status === "draft" ? "warning" : "success"}
            />
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
              <p className="text-sm font-semibold text-slate-800">Autosave status</p>
              <p className="mt-2 text-sm text-slate-600">{persistenceStatus.label}</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">Current note state</p>
              <p className="mt-2 text-sm text-slate-600">
                Drafts stay editable. Save note version when you want a formal checkpoint.
              </p>
            </div>
          </div>
        </div>

        <div className="grid gap-6 xl:grid-cols-[1.02fr_0.98fr]">
          <div className="space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-semibold text-slate-950">Capture encounter source</h2>
                <StatusBadge label="Step 1" status="neutral" />
              </div>
              <p className="mt-2 text-sm text-slate-600">
                Start here. Add the conversation and exam details first, then review the SOAP note
                on the right.
              </p>

              <div className="mt-5">
                <label className="block text-sm font-semibold text-slate-800">Transcript</label>
                <textarea
                  rows={10}
                  value={draft.transcript}
                  data-testid="transcript-input"
                  onChange={(event) => updateField("transcript", event.target.value)}
                  disabled={accountDeactivated}
                  className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                  placeholder="Paste or type the encounter transcript here. This can come from manual typing or live dictation."
                />
                <p className="mt-2 text-sm text-slate-500">
                  The transcript captures what was said during the visit. Voice editing does not
                  create the transcript; it only revises the SOAP note later.
                </p>
              </div>

              {publicEnv.enableRealtimeTranscript && !accountDeactivated ? (
                <div className="mt-6 border-t border-slate-200 pt-6">
                  <h3 className="font-semibold text-slate-950">Live dictation</h3>
                  <p className="mt-2 text-sm text-slate-600">
                    Optional. Use this if you want speech-to-text to build the transcript instead of
                    typing it manually.
                  </p>
                  <div className="mt-4">
                    <DictationPanel
                      encounterId={encounterId}
                      baseRevision={baseRevision}
                      onDraftApplied={handleRealtimeDraftApplied}
                      onError={setErrorMessage}
                    />
                  </div>
                </div>
              ) : null}

              <div className="mt-6 border-t border-slate-200 pt-6">
                <h3 className="font-semibold text-slate-950">Clinical observations</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Add exam findings, vitals, results, and anything clinically important that may not
                  appear in the transcript.
                </p>
                <textarea
                  rows={6}
                  value={draft.observations}
                  data-testid="observations-input"
                  onChange={(event) => updateField("observations", event.target.value)}
                  disabled={accountDeactivated}
                  className="mt-3 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                  placeholder="Example: BP 138/86, lungs clear, no respiratory distress, mild pharyngeal erythema."
                />
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-slate-950">SOAP note</h2>
                  <p className="mt-1 text-sm text-slate-600">
                    Step 2. Generate or write the note, then review every section before saving.
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Button
                    variant="secondary"
                    onClick={() => void handleGenerateNote()}
                    disabled={isGenerating || accountDeactivated}
                    data-testid="generate-note-button"
                  >
                    {isGenerating ? "Generating..." : "Generate SOAP note"}
                  </Button>
                  <Button
                    onClick={() => void handleSaveNote()}
                    disabled={isSavingNote || accountDeactivated}
                    data-testid="save-note-button"
                  >
                    {isSavingNote ? "Saving note..." : "Save note version"}
                  </Button>
                </div>
              </div>

              <div className="mt-4 rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-900">
                AI-generated draft. Provider review is required before finalization.
              </div>

              <p className="mt-4 text-sm text-slate-600">
                You can type directly in these sections. If transcript and observations are filled
                in, Generate SOAP note will draft the sections for you.
              </p>

              {soapSections.map(({ field, label, rows }) => (
                <div key={field} className="mt-5">
                  <label className="block text-sm font-semibold text-slate-800">{label}</label>
                  <textarea
                    rows={rows}
                    value={draft[field]}
                    data-testid={`${field}-input`}
                    onChange={(event) => updateField(field, event.target.value)}
                    disabled={accountDeactivated}
                    className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                    placeholder={`Enter ${label.toLowerCase()} content.`}
                  />
                </div>
              ))}

              <div className="mt-6 border-t border-slate-200 pt-6">
                <h3 className="font-semibold text-slate-950">Selected ICD-10 codes</h3>
                <p className="mt-2 text-sm text-slate-600">
                  Step 3. Confirm diagnosis codes after you know what belongs in the Assessment.
                </p>

                {draft.selected_icd10_codes.length === 0 ? (
                  <p className="mt-4 text-sm text-slate-600">No ICD-10 codes selected yet.</p>
                ) : (
                  <div className="mt-4 space-y-3">
                    {draft.selected_icd10_codes.map((codeEntry) => (
                      <div
                        key={codeEntry.code}
                        className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3"
                      >
                        <div>
                          <p className="text-sm font-semibold text-slate-900">{codeEntry.code}</p>
                          <p className="mt-1 text-sm text-slate-600">{codeEntry.description}</p>
                        </div>
                        <Button
                          variant="secondary"
                          className="shrink-0"
                          onClick={() => removeSelectedIcdCode(codeEntry.code)}
                          disabled={accountDeactivated}
                        >
                          Remove
                        </Button>
                      </div>
                    ))}
                  </div>
                )}

                {publicEnv.enableIcdSearch ? (
                  <div className="mt-5 rounded-lg border border-slate-200 bg-white p-4">
                    <h4 className="font-semibold text-slate-950">ICD-10 search</h4>
                    <p className="mt-2 text-sm text-slate-600">
                      Search by code, diagnosis name, or a plain-English phrase such as &quot;right
                      knee arthritis&quot;.
                    </p>

                    <div className="mt-4">
                      <label
                        htmlFor="icd-search"
                        className="block text-sm font-semibold text-slate-800"
                      >
                        Search query
                      </label>
                      <input
                        id="icd-search"
                        type="text"
                        value={icdQuery}
                        data-testid="icd-search-input"
                        onChange={(event) => setIcdQuery(event.target.value)}
                        disabled={accountDeactivated}
                        placeholder="Search ICD-10 codes"
                        className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
                      />
                    </div>

                    {isSearchingIcd ? (
                      <p className="mt-4 text-sm text-slate-600">Searching ICD-10 dataset...</p>
                    ) : null}

                    {icdSearchError ? (
                      <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {icdSearchError}
                      </div>
                    ) : null}

                    {!isSearchingIcd &&
                    icdQuery.trim().length >= 2 &&
                    icdResults.length === 0 &&
                    !icdSearchError ? (
                      <p className="mt-4 text-sm text-slate-600">No matching ICD-10 codes found.</p>
                    ) : null}

                    {icdResults.length > 0 ? (
                      <div className="mt-4 space-y-3">
                        {icdResults.map((result) => {
                          const isAlreadySelected = draft.selected_icd10_codes.some(
                            (item) => item.code === result.code,
                          );

                          return (
                            <div
                              key={result.code}
                              className="flex flex-wrap items-start justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3"
                            >
                              <div>
                                <p className="text-sm font-semibold text-slate-900">
                                  {result.code}
                                  {result.category ? ` • ${result.category}` : ""}
                                </p>
                                <p className="mt-1 text-sm text-slate-600">{result.description}</p>
                              </div>

                              <Button
                                variant={isAlreadySelected ? "secondary" : "primary"}
                                className="shrink-0"
                                onClick={() => addSelectedIcdCode(result)}
                                data-testid={`add-icd-${result.code}`}
                                disabled={isAlreadySelected || accountDeactivated}
                              >
                                {isAlreadySelected ? "Added" : "Add to assessment"}
                              </Button>
                            </div>
                          );
                        })}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>

              {publicEnv.enableVoiceAgent && !accountDeactivated ? (
                <div className="mt-6 border-t border-slate-200 pt-6">
                  <h3 className="font-semibold text-slate-950">Voice editing</h3>
                  <p className="mt-2 text-sm text-slate-600">
                    Optional. Use short commands here after a SOAP note already exists.
                  </p>
                  <div className="mt-4">
                    <VoiceEditPanel
                      encounterId={encounterId}
                      draft={draft}
                      baseRevision={baseRevision}
                      onDraftApplied={handleRealtimeDraftApplied}
                      onError={setErrorMessage}
                    />
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div
          className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          data-testid="version-history-panel"
        >
          <h2 className="font-semibold text-slate-950">Version history</h2>
          <p className="mt-2 text-sm text-slate-600">
            A version is created only when you press Save note version. Autosave protects the draft,
            but it does not create a permanent historical record.
          </p>

          {versions.length === 0 ? (
            <p className="mt-3 text-sm text-slate-600">
              No note versions saved yet. Save the note once you want a formal checkpoint.
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
                <div
                  className="rounded-lg border border-slate-200 bg-white p-4"
                  data-testid="selected-version-details"
                >
                  <h3
                    className="font-semibold text-slate-950"
                    data-testid="selected-version-heading"
                  >
                    Version {selectedVersion.version_number} details
                  </h3>
                  <p className="mt-1 text-sm text-slate-600">
                    Saved {formatDateTime(selectedVersion.saved_at)} by{" "}
                    {renderVersionAuthor(selectedVersion)}
                  </p>
                  {[
                    {
                      label: "Subjective",
                      value: selectedVersion.subjective,
                      testId: "selected-version-subjective",
                    },
                    {
                      label: "Objective",
                      value: selectedVersion.objective,
                      testId: "selected-version-objective",
                    },
                    {
                      label: "Assessment",
                      value: selectedVersion.assessment,
                      testId: "selected-version-assessment",
                    },
                    {
                      label: "Plan",
                      value: selectedVersion.plan,
                      testId: "selected-version-plan",
                    },
                  ].map(({ label, value, testId }) => (
                    <div key={label} className="mt-4" data-testid={testId}>
                      <p className="text-sm font-semibold text-slate-800">{label}</p>
                      <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm whitespace-pre-wrap text-slate-700">
                        {value || "No content saved for this section."}
                      </div>
                    </div>
                  ))}

                  <div className="mt-4">
                    <p className="text-sm font-semibold text-slate-800">ICD-10 codes</p>
                    <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                      {selectedVersion.icd10_codes && selectedVersion.icd10_codes.length > 0 ? (
                        <div className="space-y-2">
                          {selectedVersion.icd10_codes.map((codeEntry) => (
                            <div key={codeEntry.code}>
                              <span className="font-semibold">{codeEntry.code}</span>
                              {codeEntry.description ? ` — ${codeEntry.description}` : ""}
                            </div>
                          ))}
                        </div>
                      ) : (
                        "No ICD-10 codes saved for this version."
                      )}
                    </div>
                  </div>

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
                            data-testid="version-compare-select"
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
                              data-testid={`version-diff-${section.label.toLowerCase()}`}
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
                                    <div
                                      className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm whitespace-pre-wrap text-red-900"
                                      data-testid={`version-diff-${section.label.toLowerCase()}-removed`}
                                    >
                                      {section.removed || "No removed content."}
                                    </div>
                                  </div>
                                  <div>
                                    <p className="text-xs font-semibold tracking-wide text-emerald-700 uppercase">
                                      Added
                                    </p>
                                    <div
                                      className="mt-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm whitespace-pre-wrap text-emerald-900"
                                      data-testid={`version-diff-${section.label.toLowerCase()}-added`}
                                    >
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
      </div>
    </div>
  );
}
