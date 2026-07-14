from sqlalchemy import Boolean, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import BaseModel
from app.db.models.enums import UserRole


class User(BaseModel):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", validate_strings=True),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    provider_profile: Mapped["ProviderProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    created_encounters: Mapped[list["Encounter"]] = relationship(
        back_populates="provider",
        foreign_keys="Encounter.provider_id",
    )
    created_templates: Mapped[list["Template"]] = relationship(
        back_populates="created_by_user",
        foreign_keys="Template.created_by_user_id",
    )
    note_versions: Mapped[list["NoteVersion"]] = relationship(
        back_populates="saved_by_user",
        foreign_keys="NoteVersion.saved_by_user_id",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="actor_user",
        foreign_keys="AuditLog.actor_user_id",
    )

    @validates("email")
    def validate_email(self, _: str, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Email is required.")
        return normalized


from app.db.models.audit_log import AuditLog
from app.db.models.encounter import Encounter
from app.db.models.note_version import NoteVersion
from app.db.models.provider_profile import ProviderProfile
from app.db.models.template import Template
