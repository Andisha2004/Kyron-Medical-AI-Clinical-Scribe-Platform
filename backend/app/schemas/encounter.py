from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import EncounterStatus


class EncounterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    provider_id: str
    template_id: str
    status: EncounterStatus
    encounter_date: datetime


class ProviderDashboardEncounterResponse(BaseModel):
    id: str
    patient_name: str
    encounter_date: datetime
    last_updated_at: datetime
    status: EncounterStatus
    template_name: str


class ProviderDashboardResponse(BaseModel):
    provider_name: str
    draft_count: int
    completed_count: int
    encounters: list[ProviderDashboardEncounterResponse]


class CreateEncounterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    template_id: str


class CreateEncounterResponse(BaseModel):
    encounter_id: str
    patient_id: str
    draft_id: str
    reused_existing_patient: bool
    has_prior_history: bool
    prior_encounter_count: int


class EncounterDraftUpdateRequest(BaseModel):
    base_revision: int | None = None
    transcript: str | None = None
    observations: str | None = None
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    selected_icd10_codes: list[dict[str, str]] | None = None


class EncounterDraftResponse(BaseModel):
    encounter_id: str
    transcript: str | None
    observations: str | None
    subjective: str | None
    objective: str | None
    assessment: str | None
    plan: str | None
    selected_icd10_codes: list[dict[str, str]] | None
    draft_revision: int
    updated_at: datetime


class SaveEncounterNoteRequest(BaseModel):
    subjective: str | None = None
    objective: str | None = None
    assessment: str | None = None
    plan: str | None = None
    icd10_codes: list[dict[str, str]] | None = None
    generation_metadata: dict | None = None


class SaveEncounterNoteResponse(BaseModel):
    note_id: str
    version_id: str
    version_number: int
    encounter_status: EncounterStatus


class EncounterPatientResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: date


class EncounterTemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool


class EncounterVersionSummaryResponse(BaseModel):
    id: str
    version_number: int
    saved_at: datetime


class EncounterDetailResponse(BaseModel):
    id: str
    patient_id: str
    provider_id: str
    template_id: str
    status: EncounterStatus
    encounter_date: datetime
    patient: EncounterPatientResponse
    template: EncounterTemplateResponse
    draft: EncounterDraftResponse | None
    note_id: str | None
    versions: list[EncounterVersionSummaryResponse]
