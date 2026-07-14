export interface SavedByUserSummary {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
}

export interface NoteVersion {
  id: string;
  note_id: string;
  version_number: number;
  saved_by_user_id: string;
  saved_by_user: SavedByUserSummary;
  subjective: string | null;
  objective: string | null;
  assessment: string | null;
  plan: string | null;
  icd10_codes: Array<Record<string, string>> | null;
  saved_at: string;
  generation_metadata: Record<string, unknown> | null;
}
