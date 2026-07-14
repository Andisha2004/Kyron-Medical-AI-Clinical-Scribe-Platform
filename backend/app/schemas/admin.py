from datetime import date, datetime

from pydantic import BaseModel, Field


class AdminDashboardEncounterResponse(BaseModel):
    id: str
    patient_name: str
    provider_name: str
    status: str
    encounter_date: datetime
    template_name: str


class AdminDashboardResponse(BaseModel):
    active_provider_count: int
    total_encounter_count: int
    active_template_count: int
    recent_encounters: list[AdminDashboardEncounterResponse]


class AdminProviderSummaryResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    specialty: str | None
    is_active: bool
    created_at: datetime


class CreateProviderRequest(BaseModel):
    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    email: str
    password: str = Field(min_length=8)
    specialty: str | None = None


class ProviderStatusUpdateRequest(BaseModel):
    is_active: bool


class AdminEncounterListItemResponse(BaseModel):
    id: str
    provider_id: str
    provider_name: str
    patient_name: str
    encounter_date: datetime
    status: str
    template_name: str
    updated_at: datetime


class AdminEncounterListResponse(BaseModel):
    items: list[AdminEncounterListItemResponse]
    page: int
    page_size: int
    total: int


class AdminTemplateSectionInput(BaseModel):
    section: str
    instructions: str = Field(min_length=1)
    sort_order: int = Field(ge=0)
