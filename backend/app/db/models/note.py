from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel


class Note(BaseModel):
    __tablename__ = "notes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["current_version_id"],
            ["note_versions.id"],
            name="fk_notes_current_version_id_note_versions",
            ondelete="SET NULL",
            use_alter=True,
        ),
    )

    encounter_id: Mapped[str] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    current_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    encounter: Mapped["Encounter"] = relationship(back_populates="note")
    current_version: Mapped["NoteVersion | None"] = relationship(
        foreign_keys=[current_version_id],
        post_update=True,
    )
    versions: Mapped[list["NoteVersion"]] = relationship(
        back_populates="note",
        foreign_keys="NoteVersion.note_id",
        cascade="all, delete-orphan",
    )


from app.db.models.encounter import Encounter
from app.db.models.note_version import NoteVersion
