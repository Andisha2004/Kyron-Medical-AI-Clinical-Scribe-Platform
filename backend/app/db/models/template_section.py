from sqlalchemy import Enum, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel
from app.db.models.enums import TemplateSectionType


class TemplateSection(BaseModel):
    __tablename__ = "template_sections"
    __table_args__ = (
        UniqueConstraint("template_id", "section", name="uq_template_sections_template_section"),
        Index("ix_template_sections_template_id_sort_order", "template_id", "sort_order"),
    )

    template_id: Mapped[str] = mapped_column(
        ForeignKey("templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    section: Mapped[TemplateSectionType] = mapped_column(
        Enum(TemplateSectionType, name="template_section_type", validate_strings=True),
        nullable=False,
    )
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    template: Mapped["Template"] = relationship(back_populates="sections")


from app.db.models.template import Template
