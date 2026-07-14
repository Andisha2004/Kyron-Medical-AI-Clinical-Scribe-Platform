from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.schemas.voice import DictationPatchOperation, DictationSegmentRequest, SoapSection
from app.services.audit_service import AuditService

SECTION_ORDER: tuple[SoapSection, ...] = ("subjective", "objective", "assessment", "plan")


@dataclass
class DictationSegmentResult:
    accepted: bool
    transcript_appended: bool
    transcript_preview: str
    partial_transcript: str | None
    operations: list[DictationPatchOperation]
    draft: EncounterDraft


class DictationService:
    async def process_segment(
        self,
        *,
        session: AsyncSession,
        encounter: Encounter,
        payload: DictationSegmentRequest,
        actor_user_id: str,
    ) -> DictationSegmentResult:
        draft = await session.scalar(
            select(EncounterDraft).where(EncounterDraft.encounter_id == encounter.id)
        )
        if draft is None:
            draft = EncounterDraft(
                encounter_id=encounter.id,
                transcript="",
                observations="",
                subjective="",
                objective="",
                assessment="",
                plan="",
                selected_icd10_codes=[],
                draft_revision=1,
            )
            session.add(draft)
            await session.flush()

        if payload.base_revision is not None and payload.base_revision != draft.draft_revision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Draft revision conflict.",
            )

        normalized_segment = " ".join(payload.transcript_segment.strip().split())
        if not normalized_segment:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Transcript segment cannot be empty.",
            )

        if not payload.is_final:
            return DictationSegmentResult(
                accepted=True,
                transcript_appended=False,
                transcript_preview=(draft.transcript or "").strip(),
                partial_transcript=normalized_segment,
                operations=[],
                draft=draft,
            )

        transcript_appended = self.append_transcript_segment(draft, normalized_segment)
        operations: list[DictationPatchOperation] = []
        if transcript_appended:
            operation = self.build_incremental_patch(draft, normalized_segment)
            if operation is not None:
                self.apply_patch_operation(draft, operation)
                operations.append(operation)

        await AuditService.log_event(
            session,
            actor_user_id=actor_user_id,
            action="DICTATION_SEGMENT_PROCESSED",
            entity_type="encounter_draft",
            entity_id=draft.id,
            metadata_json={
                "encounter_id": encounter.id,
                "is_final": payload.is_final,
                "operations_count": len(operations),
                "segment_id": payload.segment_id,
            },
        )
        await session.commit()
        await session.refresh(draft)

        return DictationSegmentResult(
            accepted=True,
            transcript_appended=transcript_appended,
            transcript_preview=(draft.transcript or "").strip(),
            partial_transcript=None,
            operations=operations,
            draft=draft,
        )

    def append_transcript_segment(self, draft: EncounterDraft, segment: str) -> bool:
        existing_transcript = (draft.transcript or "").strip()
        if self.is_duplicate_segment(existing_transcript, segment):
            return False

        if existing_transcript:
            draft.transcript = f"{existing_transcript}\n{segment}"
        else:
            draft.transcript = segment
        return True

    def is_duplicate_segment(self, transcript: str, segment: str) -> bool:
        if not transcript:
            return False

        transcript_lines = [line.strip().lower() for line in transcript.splitlines() if line.strip()]
        segment_lower = segment.lower()
        return segment_lower in transcript_lines

    def build_incremental_patch(
        self, draft: EncounterDraft, segment: str
    ) -> DictationPatchOperation | None:
        section = self.infer_target_section(segment)
        section_text = getattr(draft, section) or ""

        if segment.lower() in section_text.lower():
            return None

        return DictationPatchOperation(operation="append", section=section, text=segment)

    def infer_target_section(self, segment: str) -> SoapSection:
        lowered = segment.lower()

        if any(
            keyword in lowered
            for keyword in (
                "continue ",
                "start ",
                "stop ",
                "increase ",
                "decrease ",
                "follow up",
                "return in",
                "return if",
                "order ",
                "prescribe",
                "plan:",
            )
        ):
            return "plan"

        if any(
            keyword in lowered
            for keyword in (
                "blood pressure",
                "temperature",
                "heart rate",
                "pulse",
                "exam",
                "swelling",
                "range of motion",
                "tenderness",
                "objective:",
            )
        ):
            return "objective"

        if any(
            keyword in lowered
            for keyword in (
                "diagnosis",
                "assessment",
                "osteoarthritis",
                "viral uri",
                "hypertension",
                "assessment:",
            )
        ):
            return "assessment"

        return "subjective"

    def apply_patch_operation(self, draft: EncounterDraft, operation: DictationPatchOperation) -> None:
        current = (getattr(draft, operation.section) or "").strip()
        updated = f"{current}\n{operation.text}" if current else operation.text
        setattr(draft, operation.section, updated.strip())


def get_dictation_service() -> DictationService:
    return DictationService()
