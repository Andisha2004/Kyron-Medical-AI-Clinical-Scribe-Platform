from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import BaseModel


class Icd10Code(BaseModel):
    __tablename__ = "icd10_codes"
    __table_args__ = (
        Index("ix_icd10_codes_code", "code"),
        Index("ix_icd10_codes_category", "category"),
        Index("ix_icd10_codes_search_text", "search_text"),
    )

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)

    @validates("code", "description", "search_text")
    def validate_required_text(self, key: str, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{key.replace('_', ' ').title()} is required.")
        return cleaned
