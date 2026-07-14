from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.models.enums import EncounterStatus


class Encounter(BaseModel):
    __tablename__ = "encounters"
    __table_args__ = (
        Index("ix_encounters_provider_id", "provider_id"),
        Index("ix_encounters_patient_id", "patient_id"),
        Index("ix_encounters_template_id", "template_id"),
        Index("ix_encounters_status", "status"),
        Index("ix_encounters_encounter_date", "encounter_date"),
        Index("ix_encounters_provider_date", "provider_id", "encounter_date"),
    )

    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_id: Mapped[str] = mapped_column(
        ForeignKey("templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[EncounterStatus] = mapped_column(
        Enum(EncounterStatus, name="encounter_status", validate_strings=True),
        nullable=False,
        default=EncounterStatus.DRAFT,
    )
    encounter_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    patient: Mapped["Patient"] = relationship(back_populates="encounters")
    provider: Mapped["User"] = relationship(
        back_populates="created_encounters",
        foreign_keys=[provider_id],
    )
    template: Mapped["Template"] = relationship(back_populates="encounters")
    draft: Mapped["EncounterDraft | None"] = relationship(
        back_populates="encounter",
        uselist=False,
        cascade="all, delete-orphan",
    )
    note: Mapped["Note | None"] = relationship(
        back_populates="encounter",
        uselist=False,
        cascade="all, delete-orphan",
    )


from app.db.models.encounter_draft import EncounterDraft
from app.db.models.note import Note
from app.db.models.patient import Patient
from app.db.models.template import Template
from app.db.models.user import User
