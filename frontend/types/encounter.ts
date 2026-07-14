export type EncounterStatus = "draft" | "completed";

export interface EncounterListItem {
  id: string;
  patient_name: string;
  encounter_date: string;
  last_updated_at: string;
  status: EncounterStatus;
  template_name: string;
}

export interface ProviderDashboardResponse {
  provider_name: string;
  draft_count: number;
  completed_count: number;
  encounters: EncounterListItem[];
}

export interface CreateEncounterRequest {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  template_id: string;
}

export interface CreateEncounterResponse {
  encounter_id: string;
  patient_id: string;
  draft_id: string;
  reused_existing_patient: boolean;
  has_prior_history: boolean;
  prior_encounter_count: number;
}

export interface DraftState {
  transcript: string;
  observations: string;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  selected_icd10_codes: Array<Record<string, string>>;
}

export interface EncounterDraftResponse extends DraftState {
  encounter_id: string;
  draft_revision: number;
  updated_at: string;
}

export interface EncounterPatient {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
}

export interface EncounterTemplate {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
}

export interface EncounterVersionSummary {
  id: string;
  version_number: number;
  saved_at: string;
}

export interface EncounterDetailResponse {
  id: string;
  patient_id: string;
  provider_id: string;
  template_id: string;
  status: EncounterStatus;
  encounter_date: string;
  patient: EncounterPatient;
  template: EncounterTemplate;
  draft: EncounterDraftResponse | null;
  note_id: string | null;
  versions: EncounterVersionSummary[];
}

export interface UpdateEncounterDraftRequest extends DraftState {
  base_revision: number | null;
}

export interface SaveEncounterNoteRequest {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  icd10_codes: Array<Record<string, string>>;
  idempotency_key: string;
  generation_metadata?: Record<string, unknown> | null;
}

export interface SaveEncounterNoteResponse {
  note_id: string;
  version_id: string;
  version_number: number;
  encounter_status: EncounterStatus;
}
