from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.clients.openai_client import get_openai_clinical_scribe_client
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.template import Template
from app.db.models.template_section import TemplateSection
from app.schemas.generation import SoapNoteGenerationResult
from app.services.audit_service import AuditService
from app.services.patient_history_service import PatientHistoryService

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class ClinicalScribeClient(Protocol):
    async def generate_soap_note(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> SoapNoteGenerationResult: ...


class InsufficientClinicalContentError(Exception):
    pass


class NoteGenerationService:
    def __init__(
        self,
        *,
        ai_client: ClinicalScribeClient,
        patient_history_service: PatientHistoryService | None = None,
    ) -> None:
        self.ai_client = ai_client
        self.patient_history_service = patient_history_service or PatientHistoryService()

    async def generate_for_encounter(
        self,
        session: AsyncSession,
        *,
        encounter: Encounter,
    ) -> tuple[SoapNoteGenerationResult, EncounterDraft]:
        encounter_with_relations = await session.scalar(
            select(Encounter)
            .where(Encounter.id == encounter.id)
            .options(
                selectinload(Encounter.draft),
                selectinload(Encounter.template).selectinload(Template.sections),
            )
        )
        if encounter_with_relations is None:
            raise ValueError("Encounter not found.")

        draft = encounter_with_relations.draft
        if draft is None:
            draft = EncounterDraft(encounter_id=encounter.id, draft_revision=1)
            session.add(draft)
            await session.flush()

        clinical_text = self._build_clinical_text(draft)
        if not self._has_meaningful_clinical_content(clinical_text):
            raise InsufficientClinicalContentError(
                "There is not enough clinical information to generate a reliable SOAP note. Add symptoms, medical history, examination findings, or treatment details."
            )

        template = encounter_with_relations.template
        if not template.is_active or template.deleted_at is not None:
            raise ValueError("Encounter template is inactive.")

        patient_history = await self.patient_history_service.get_relevant_history(
            session,
            encounter=encounter_with_relations,
        )
        system_prompt = self._build_system_prompt(template.sections)
        user_prompt = self._build_user_prompt(
            encounter=encounter_with_relations,
            draft=draft,
            patient_history=patient_history,
        )
        result = await self.ai_client.generate_soap_note(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        draft.subjective = result.subjective
        draft.objective = result.objective
        draft.assessment = self._format_assessment_for_ui(result)
        draft.plan = result.plan
        draft.selected_icd10_codes = [
            {
                "code": item.icd10_code or "",
                "description": item.description or item.diagnosis,
                "diagnosis": item.diagnosis,
            }
            for item in result.assessment
            if item.icd10_code or item.description or item.diagnosis
        ]
        await session.flush()
        await AuditService.log_event(
            session,
            actor_user_id=encounter.provider_id,
            action="NOTE_GENERATED",
            entity_type="encounter",
            entity_id=encounter.id,
            metadata_json={
                "draft_revision": draft.draft_revision,
                "missing_information_count": len(result.missing_information),
                "warning_count": len(result.warnings),
            },
        )
        await session.commit()
        await session.refresh(draft)
        return result, draft

    @staticmethod
    def _build_clinical_text(draft: EncounterDraft) -> str:
        return "\n".join(
            value.strip()
            for value in [draft.transcript or "", draft.observations or ""]
            if value and value.strip()
        )

    @staticmethod
    def _has_meaningful_clinical_content(text: str) -> bool:
        cleaned = text.strip().lower()
        if len(cleaned) < 40:
            return False

        clinical_terms = {
            "pain",
            "fever",
            "cough",
            "blood pressure",
            "denies",
            "reports",
            "patient",
            "symptom",
            "follow-up",
            "history",
            "exam",
            "swelling",
            "injury",
            "medication",
            "therapy",
        }
        return any(term in cleaned for term in clinical_terms)

    @staticmethod
    def _format_assessment_for_ui(result: SoapNoteGenerationResult) -> str:
        if not result.assessment:
            return ""

        lines = []
        for index, item in enumerate(result.assessment, start=1):
            details = [item.diagnosis]
            if item.icd10_code:
                details.append(f"ICD-10: {item.icd10_code}")
            if item.description:
                details.append(item.description)
            lines.append(f"{index}. " + " — ".join(part for part in details if part))
        return "\n".join(lines)

    @staticmethod
    def _build_system_prompt(template_sections: list[TemplateSection]) -> str:
        base_prompt = (PROMPTS_DIR / "base_scribe.txt").read_text()
        template_instructions = "\n".join(
            f"{section.section.value.title()}: {section.instructions.strip()}"
            for section in sorted(template_sections, key=lambda item: (item.sort_order, item.section.value))
        )
        return base_prompt.replace("{{TEMPLATE_SECTION_INSTRUCTIONS}}", template_instructions)

    @staticmethod
    def _build_user_prompt(
        *,
        encounter: Encounter,
        draft: EncounterDraft,
        patient_history,
    ) -> str:
        history_lines = "\n".join(f"- {item.summary}" for item in patient_history.items) or "- None"
        transcript = draft.transcript.strip() if draft.transcript else "Not provided."
        observations = draft.observations.strip() if draft.observations else "Not provided."
        return (
            f"Encounter ID: {encounter.id}\n"
            f"Current transcript:\n{transcript}\n\n"
            f"Current clinical observations:\n{observations}\n\n"
            f"Relevant prior patient history:\n{history_lines}\n"
        )


def get_note_generation_service() -> NoteGenerationService:
    return NoteGenerationService(ai_client=get_openai_clinical_scribe_client())
