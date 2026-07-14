import { api } from "@/lib/api";
import type {
  CreateEncounterRequest,
  CreateEncounterResponse,
  EncounterDetailResponse,
  EncounterDraftResponse,
  ProviderDashboardResponse,
  SaveEncounterNoteRequest,
  SaveEncounterNoteResponse,
  UpdateEncounterDraftRequest,
} from "@/types/encounter";

export async function getProviderDashboard(): Promise<ProviderDashboardResponse> {
  return api.get<ProviderDashboardResponse>("/api/encounters");
}

export async function createEncounter(
  payload: CreateEncounterRequest,
): Promise<CreateEncounterResponse> {
  return api.post<CreateEncounterResponse>("/api/encounters", payload);
}

export async function getEncounterDetail(encounterId: string): Promise<EncounterDetailResponse> {
  return api.get<EncounterDetailResponse>(`/api/encounters/${encounterId}`);
}

export async function updateEncounterDraft(
  encounterId: string,
  payload: UpdateEncounterDraftRequest,
): Promise<EncounterDraftResponse> {
  return api.patch<EncounterDraftResponse>(`/api/encounters/${encounterId}/draft`, payload);
}

export async function saveEncounterNote(
  encounterId: string,
  payload: SaveEncounterNoteRequest,
): Promise<SaveEncounterNoteResponse> {
  return api.post<SaveEncounterNoteResponse>(`/api/encounters/${encounterId}/save`, payload);
}
