from datetime import date

from sqlalchemy import Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import BaseModel


class Patient(BaseModel):
    __tablename__ = "patients"
    __table_args__ = (
        Index(
            "ix_patients_normalized_name_dob",
            "normalized_last_name",
            "normalized_first_name",
            "date_of_birth",
        ),
    )

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    normalized_first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )
    normalized_last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="",
    )

    encounters: Mapped[list["Encounter"]] = relationship(back_populates="patient")

    @staticmethod
    def normalize_name(value: str) -> str:
        return value.strip().lower()

    @validates("first_name", "last_name")
    def validate_and_normalize_name(self, key: str, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{key.replace('_', ' ').title()} is required.")

        normalized = self.normalize_name(cleaned)
        if key == "first_name":
            self.normalized_first_name = normalized
        elif key == "last_name":
            self.normalized_last_name = normalized

        return cleaned


from app.db.models.encounter import Encounter
