from datetime import UTC, date, datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.api.templates import _build_sections, serialize_template
from app.db.models.audit_log import AuditLog
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus, TemplateSectionType, UserRole
from app.db.models.icd10_code import Icd10Code
from app.db.models.patient import Patient
from app.db.models.template import Template
from app.db.models.template_section import TemplateSection
from app.db.models.user import User
from app.schemas.generation import SoapNoteGenerationResult
from app.schemas.template import TemplateSectionInput
from app.schemas.voice import DictationPatchOperation, VoiceEditOperation
from app.services.audit_service import AuditService
from app.services.dictation_service import DictationService
from app.services.icd_service import IcdService
from app.services.note_generation_service import NoteGenerationService
from app.services.voice_edit_service import VoiceEditService


def create_user(email: str, role: UserRole) -> User:
    return User(
        email=email,
        password_hash="hashed-password",
        role=role,
        is_active=True,
    )


def test_note_output_validation_rejects_malformed_assessment_items() -> None:
    with pytest.raises(ValidationError):
        SoapNoteGenerationResult.model_validate(
            {
                "subjective": "Patient reports knee pain.",
                "assessment": [{}],
            }
        )


def test_insufficient_content_detection_heuristic_filters_meaningless_input() -> None:
    assert (
        NoteGenerationService._has_meaningful_clinical_content("hello hello hello how are you today")
        is False
    )
    assert (
        NoteGenerationService._has_meaningful_clinical_content(
            "Patient reports right knee pain for three days and denies fever after the injury."
        )
        is True
    )


def test_template_building_and_serialization_enforce_consistency() -> None:
    built_sections = _build_sections(
        [
            TemplateSectionInput(
                section="plan",
                instructions="Plan instructions",
                sort_order=4,
            ),
            TemplateSectionInput(
                section="subjective",
                instructions="Subjective instructions",
                sort_order=1,
            ),
        ]
    )
    assert [section.section for section in built_sections] == [
        TemplateSectionType.PLAN,
        TemplateSectionType.SUBJECTIVE,
    ]

    template = Template(
        name="Serialization Template",
        description="Tests ordered template output.",
        is_active=True,
        created_by_user_id="creator-id",
    )
    template.id = "template-id"
    template.sections = [
        TemplateSection(
            id="section-plan",
            section=TemplateSectionType.PLAN,
            instructions="Plan instructions",
            sort_order=4,
        ),
        TemplateSection(
            id="section-subjective",
            section=TemplateSectionType.SUBJECTIVE,
            instructions="Subjective instructions",
            sort_order=1,
        ),
    ]

    serialized = serialize_template(template)
    assert [section.section for section in serialized.sections] == ["subjective", "plan"]

    with pytest.raises(HTTPException) as exc_info:
        _build_sections(
            [
                TemplateSectionInput(
                    section="subjective",
                    instructions="One",
                    sort_order=1,
                ),
                TemplateSectionInput(
                    section="subjective",
                    instructions="Two",
                    sort_order=2,
                ),
            ]
        )
    assert exc_info.value.status_code == 422


def test_dictation_patch_application_and_voice_patch_application() -> None:
    draft = EncounterDraft(
        encounter_id="encounter-id",
        transcript="Patient reports knee pain.",
        subjective="Patient reports knee pain.",
        objective="Mild swelling noted.",
        assessment="Knee pain.",
        plan="Follow up in two weeks.",
        selected_icd10_codes=[],
        draft_revision=1,
    )

    dictation_service = DictationService()
    dictation_service.apply_patch_operation(
        draft,
        DictationPatchOperation(
            operation="append",
            section="plan",
            text="Continue home exercises.",
        ),
    )
    assert "Continue home exercises." in (draft.plan or "")

    voice_service = VoiceEditService()
    updated_section, updated_text, changed = voice_service.apply_operation(
        draft,
        VoiceEditOperation(
            operation="move",
            source_section="objective",
            target_section="subjective",
            target_text="Mild swelling noted.",
        ),
    )
    assert updated_section == "subjective"
    assert "Mild swelling noted." in updated_text
    assert "Mild swelling noted." not in (draft.objective or "")
    assert changed is True


def test_voice_service_interprets_natural_spoken_note_content_as_append() -> None:
    draft = EncounterDraft(
        encounter_id="encounter-id",
        transcript="",
        subjective="Patient reports cough.",
        objective="",
        assessment="",
        plan="",
        selected_icd10_codes=[],
        draft_revision=1,
    )

    voice_service = VoiceEditService()
    operation = voice_service.interpret_command(
        "the patient is saying that they are having very high fever and cannot sleep",
        draft,
    )

    assert operation.operation == "append"
    assert operation.target_section == "subjective"
    assert operation.new_text == "Patient reports they are having very high fever and cannot sleep."


def test_voice_service_rejects_meta_rewrite_requests_without_a_model() -> None:
    draft = EncounterDraft(
        encounter_id="encounter-id",
        transcript="",
        subjective="Patient reports cough.",
        objective="",
        assessment="",
        plan="",
        selected_icd10_codes=[],
        draft_revision=1,
    )

    voice_service = VoiceEditService()

    with pytest.raises(HTTPException) as exc_info:
        voice_service.interpret_command("add all the notes to the soap notes and make it better", draft)

    assert exc_info.value.status_code == 422
    assert "rewrite-style model" in str(exc_info.value.detail)


def test_voice_service_shorten_reports_when_text_is_already_concise() -> None:
    draft = EncounterDraft(
        encounter_id="encounter-id",
        transcript="",
        subjective="",
        objective="",
        assessment="",
        plan="Recommend supportive care.",
        selected_icd10_codes=[],
        draft_revision=1,
    )

    voice_service = VoiceEditService()
    operation = voice_service.interpret_command("Shorten the Plan", draft)
    updated_section, updated_text, changed = voice_service.apply_operation(draft, operation)
    response = voice_service.build_assistant_response(operation, updated_section, changed)

    assert updated_section == "plan"
    assert updated_text == "Recommend supportive care."
    assert changed is False
    assert response == "Plan was already concise, so I left it unchanged."


def test_icd_ranking_prefers_exact_code_matches() -> None:
    service = IcdService()
    exact_match = Icd10Code(
        code="M25.561",
        description="Pain in right knee",
        category="Symptoms",
        search_text="right knee pain arthralgia knee pain",
    )
    description_match = Icd10Code(
        code="M17.11",
        description="Unilateral primary osteoarthritis, right knee",
        category="Orthopedic",
        search_text="right knee osteoarthritis chronic joint pain",
    )

    exact_score = service._score_code(
        exact_match,
        normalized_query="m25 561",
        normalized_query_code="m25561",
        query_tokens={"m25", "561"},
    )
    description_score = service._score_code(
        description_match,
        normalized_query="m25 561",
        normalized_query_code="m25561",
        query_tokens={"m25", "561"},
    )

    assert exact_score > description_score


@pytest.mark.asyncio
async def test_audit_service_writes_metadata_to_database(db_session) -> None:
    actor = create_user("audit.service@example.com", UserRole.ADMIN)
    patient = Patient(first_name="Jordan", last_name="Audit", date_of_birth=date(1990, 1, 1))
    template = Template(
        name="Audit Template",
        description="Template for audit tests.",
        is_active=True,
        created_by_user=actor,
    )
    encounter = Encounter(
        patient=patient,
        provider=actor,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime.now(UTC),
    )
    db_session.add_all([actor, patient, template, encounter])
    await db_session.flush()

    await AuditService.log_event(
        db_session,
        actor_user_id=actor.id,
        action="PHASE13_AUDIT_TEST",
        entity_type="encounter",
        entity_id=encounter.id,
        metadata={"source": "unit-test", "severity": "info"},
    )
    await db_session.commit()

    audit_log = await db_session.scalar(
        select(AuditLog).where(AuditLog.action == "PHASE13_AUDIT_TEST")
    )
    assert audit_log is not None
    assert audit_log.actor_user_id == actor.id
    assert audit_log.metadata_json == {"source": "unit-test", "severity": "info"}
