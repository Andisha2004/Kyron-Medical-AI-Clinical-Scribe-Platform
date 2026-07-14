from sqlalchemy import event
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class EncounterDraft(BaseModel):
    __tablename__ = "encounter_drafts"

    encounter_id: Mapped[str] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    subjective: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_icd10_codes: Mapped[list[dict[str, str]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    draft_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    encounter: Mapped["Encounter"] = relationship(back_populates="draft")


from app.db.models.encounter import Encounter


@event.listens_for(EncounterDraft, "before_update", propagate=True)
def increment_draft_revision(mapper, connection, target: EncounterDraft) -> None:
    target.draft_revision += 1
