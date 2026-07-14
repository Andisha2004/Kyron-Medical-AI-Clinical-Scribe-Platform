from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import BaseModel


class Template(BaseModel):
    __tablename__ = "templates"
    __table_args__ = (
        Index("ix_templates_is_active", "is_active"),
        Index("ix_templates_deleted_at", "deleted_at"),
    )

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_by_user: Mapped["User"] = relationship(
        back_populates="created_templates",
        foreign_keys=[created_by_user_id],
    )
    sections: Mapped[list["TemplateSection"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
    )
    encounters: Mapped[list["Encounter"]] = relationship(back_populates="template")

    @validates("name")
    def validate_name(self, _: str, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Template name is required.")
        return cleaned


from app.db.models.encounter import Encounter
from app.db.models.template_section import TemplateSection
from app.db.models.user import User
