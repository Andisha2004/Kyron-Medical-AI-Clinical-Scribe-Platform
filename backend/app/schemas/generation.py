from typing import Literal

from pydantic import BaseModel, Field


class AssessmentItem(BaseModel):
    diagnosis: str
    icd10_code: str | None = None
    description: str | None = None


class SoapNoteGenerationResult(BaseModel):
    subjective: str = ""
    objective: str = ""
    assessment: list[AssessmentItem] = Field(default_factory=list)
    plan: str = ""
    missing_information: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StreamingGenerationEvent(BaseModel):
    event: Literal[
        "generation_started",
        "section_delta",
        "assessment_code",
        "warning",
        "draft_saved",
        "generation_complete",
        "generation_error",
    ]
    data: dict


class PatientHistoryItem(BaseModel):
    note_version_id: str
    saved_at: str
    summary: str


class PatientHistorySummary(BaseModel):
    patient_id: str
    items: list[PatientHistoryItem] = Field(default_factory=list)
