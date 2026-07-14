from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, event, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel, utc_now


class NoteVersion(BaseModel):
    __tablename__ = "note_versions"
    __table_args__ = (
        UniqueConstraint("note_id", "version_number", name="uq_note_versions_note_version"),
        Index("ix_note_versions_note_id_created_at", "note_id", "created_at"),
    )

    note_id: Mapped[str] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    saved_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    subjective: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    icd10_codes: Mapped[list[dict[str, str]] | None] = mapped_column(JSONB, nullable=True)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )
    generation_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    note: Mapped["Note"] = relationship(
        back_populates="versions",
        foreign_keys=[note_id],
    )
    saved_by_user: Mapped["User"] = relationship(
        back_populates="note_versions",
        foreign_keys=[saved_by_user_id],
    )


from app.db.models.note import Note
from app.db.models.user import User


@event.listens_for(NoteVersion, "before_update", propagate=True)
def prevent_note_version_updates(mapper, connection, target: NoteVersion) -> None:
    raise ValueError("Note versions are immutable and cannot be updated.")
