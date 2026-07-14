export type EncounterStatus =
  "draft" | "recording" | "processing" | "ready_for_review" | "completed" | "failed";

export interface Encounter {
  id: string;
  providerId: string;
  patientDisplayName: string;
  chiefComplaint: string | null;
  status: EncounterStatus;
  createdAt: string;
  updatedAt: string;
}

export interface CreateEncounterRequest {
  patientDisplayName: string;
  chiefComplaint?: string;
}
