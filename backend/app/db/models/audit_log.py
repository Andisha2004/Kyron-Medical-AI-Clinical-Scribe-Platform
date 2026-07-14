from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_entity_lookup", "entity_type", "entity_id"),
    )

    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    actor_user: Mapped["User | None"] = relationship(
        back_populates="audit_logs",
        foreign_keys=[actor_user_id],
    )

    @validates("action", "entity_type")
    def validate_required_fields(self, key: str, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{key.replace('_', ' ').title()} is required.")
        return cleaned

    @validates("metadata_json")
    def validate_metadata(self, _: str, value: dict | None) -> dict | None:
        if value is None:
            return None

        forbidden_keys = {
            "transcript",
            "subjective",
            "objective",
            "assessment",
            "plan",
            "clinical_note",
            "note_text",
        }
        overlapping_keys = forbidden_keys.intersection(value.keys())
        if overlapping_keys:
            blocked = ", ".join(sorted(overlapping_keys))
            raise ValueError(
                f"Audit metadata cannot contain full clinical note fields: {blocked}."
            )

        return value


from app.db.models.user import User
