from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.encounter import Encounter
from app.db.models.enums import EncounterStatus
from app.db.models.note import Note
from app.db.models.note_version import NoteVersion
from app.schemas.generation import PatientHistoryItem, PatientHistorySummary


class PatientHistoryService:
    async def get_relevant_history(
        self,
        session: AsyncSession,
        *,
        encounter: Encounter,
        limit: int = 3,
    ) -> PatientHistorySummary:
        prior_encounters = await session.scalars(
            select(Encounter)
            .where(
                Encounter.patient_id == encounter.patient_id,
                Encounter.id != encounter.id,
                Encounter.status == EncounterStatus.COMPLETED,
            )
            .options(selectinload(Encounter.note).selectinload(Note.versions))
            .order_by(Encounter.encounter_date.desc())
            .limit(5)
        )

        items: list[PatientHistoryItem] = []
        for prior_encounter in prior_encounters.unique().all():
            if prior_encounter.note is None or not prior_encounter.note.versions:
                continue

            latest_version = max(
                prior_encounter.note.versions,
                key=lambda version: version.version_number,
            )
            summary = self._summarize_version(latest_version)
            if not summary:
                continue
            items.append(
                PatientHistoryItem(
                    note_version_id=latest_version.id,
                    saved_at=latest_version.saved_at.isoformat(),
                    summary=summary,
                )
            )
            if len(items) >= limit:
                break

        return PatientHistorySummary(patient_id=encounter.patient_id, items=items)

    @staticmethod
    def _summarize_version(version: NoteVersion) -> str:
        parts: list[str] = []
        if version.assessment:
            parts.append(f"Assessment: {version.assessment.strip()}")
        if version.plan:
            parts.append(f"Plan: {version.plan.strip()}")
        if version.subjective and not parts:
            parts.append(f"Subjective: {version.subjective.strip()}")
        return " ".join(parts).strip()
