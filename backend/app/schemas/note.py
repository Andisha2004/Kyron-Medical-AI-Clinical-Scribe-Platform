from datetime import datetime

from pydantic import BaseModel


class NoteVersionResponse(BaseModel):
    id: str
    note_id: str
    version_number: int
    saved_by_user_id: str
    subjective: str | None
    objective: str | None
    assessment: str | None
    plan: str | None
    icd10_codes: list[dict[str, str]] | None
    saved_at: datetime
    generation_metadata: dict | None
