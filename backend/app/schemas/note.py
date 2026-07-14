from datetime import datetime

from pydantic import BaseModel


class SavedByUserSummary(BaseModel):
    id: str
    email: str
    first_name: str | None
    last_name: str | None


class NoteVersionResponse(BaseModel):
    id: str
    note_id: str
    version_number: int
    saved_by_user_id: str
    saved_by_user: SavedByUserSummary
    subjective: str | None
    objective: str | None
    assessment: str | None
    plan: str | None
    icd10_codes: list[dict[str, str]] | None
    saved_at: datetime
    generation_metadata: dict | None
