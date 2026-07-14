from datetime import UTC, date, datetime, timedelta
import json

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus, TemplateSectionType, UserRole
from app.db.models.note import Note
from app.db.models.note_version import NoteVersion
from app.db.models.patient import Patient
from app.db.models.template import Template
from app.db.models.template_section import TemplateSection
from app.db.models.user import User
from app.schemas.generation import AssessmentItem, SoapNoteGenerationResult
from app.services.note_generation_service import NoteGenerationService, get_note_generation_service
from app.services.patient_history_service import PatientHistoryService
from app.clients.openai_client import AiClientError


class FakeClinicalScribeClient:
    def __init__(self) -> None:
        self.system_prompt: str | None = None
        self.user_prompt: str | None = None

    async def generate_soap_note(self, *, system_prompt: str, user_prompt: str) -> SoapNoteGenerationResult:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        if "right knee pain" in user_prompt.lower():
            history_suffix = ""
            if "physical therapy" in user_prompt.lower():
                history_suffix = " The patient returns after physical therapy with partial improvement."
            return SoapNoteGenerationResult(
                subjective=f"Patient reports chronic right knee pain worsened on stairs.{history_suffix} The patient denies fever.",
                objective="No vital signs or physical examination findings were provided.",
                assessment=[
                    AssessmentItem(
                        diagnosis="Right knee osteoarthritis",
                        icd10_code="M17.11",
                        description="Unilateral primary osteoarthritis, right knee",
                    )
                ],
                plan="Continue physical therapy and consider follow-up evaluation.",
                missing_information=["Physical examination details were not provided."],
                warnings=[],
            )
        return SoapNoteGenerationResult(
            subjective="Patient reports cough and sore throat for three days. Patient denies fever.",
            objective="No objective measurements were provided.",
            assessment=[
                AssessmentItem(
                    diagnosis="Upper respiratory infection",
                    icd10_code="J06.9",
                    description="Acute upper respiratory infection, unspecified",
                )
            ],
            plan="Supportive care and follow-up if symptoms worsen.",
            missing_information=[],
            warnings=[],
        )


class FailingClinicalScribeClient:
    async def generate_soap_note(self, *, system_prompt: str, user_prompt: str) -> SoapNoteGenerationResult:
        raise AiClientError("The AI note generation service timed out. Please retry.")


def create_user(email: str, role: UserRole) -> User:
    return User(
        email=email,
        password_hash=hash_password("DemoPass123!"),
        role=role,
        is_active=True,
    )


async def sign_in(client, email: str, password: str = "DemoPass123!") -> None:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def build_template(*, creator_id: str) -> Template:
    template = Template(
        name="Orthopedic Follow-Up",
        description="Focused musculoskeletal follow-up",
        is_active=True,
        created_by_user_id=creator_id,
    )
    template.sections = [
        TemplateSection(
            section=TemplateSectionType.SUBJECTIVE,
            instructions="Emphasize pain duration, severity, aggravating factors, and response to prior therapy.",
            sort_order=1,
        ),
        TemplateSection(
            section=TemplateSectionType.OBJECTIVE,
            instructions="Describe provided physical findings and clearly note if none were documented.",
            sort_order=2,
        ),
        TemplateSection(
            section=TemplateSectionType.ASSESSMENT,
            instructions="Suggest likely diagnoses and reviewable ICD-10 codes.",
            sort_order=3,
        ),
        TemplateSection(
            section=TemplateSectionType.PLAN,
            instructions="Provide concise follow-up and treatment next steps.",
            sort_order=4,
        ),
    ]
    return template


def parse_sse_events(raw_text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in raw_text.strip().split("\n\n"):
        if not block.strip():
            continue
        lines = block.splitlines()
        event_name = ""
        data = {}
        for line in lines:
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            if line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        if event_name:
            events.append((event_name, data))
    return events


@pytest.mark.asyncio
async def test_patient_history_service_returns_empty_for_first_time_patient(db_session) -> None:
    provider = create_user("history.firsttime.provider@example.com", UserRole.PROVIDER)
    admin = create_user("history.firsttime.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    template = build_template(creator_id=admin.id)
    patient = Patient(first_name="Jamie", last_name="First", date_of_birth=date(1990, 1, 1))
    db_session.add_all([template, patient])
    await db_session.flush()

    encounter = Encounter(
        patient_id=patient.id,
        provider_id=provider.id,
        template_id=template.id,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime.now(UTC),
    )
    db_session.add(encounter)
    await db_session.commit()

    history = await PatientHistoryService().get_relevant_history(db_session, encounter=encounter)
    assert history.items == []


@pytest.mark.asyncio
async def test_patient_history_service_returns_prior_context(db_session) -> None:
    provider = create_user("history.returning.provider@example.com", UserRole.PROVIDER)
    admin = create_user("history.returning.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    template = build_template(creator_id=admin.id)
    patient = Patient(first_name="Jordan", last_name="History", date_of_birth=date(1989, 4, 12))
    db_session.add_all([template, patient])
    await db_session.flush()

    prior_encounter = Encounter(
        patient_id=patient.id,
        provider_id=provider.id,
        template_id=template.id,
        status=EncounterStatus.COMPLETED,
        encounter_date=datetime.now(UTC) - timedelta(days=30),
    )
    current_encounter = Encounter(
        patient_id=patient.id,
        provider_id=provider.id,
        template_id=template.id,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime.now(UTC),
    )
    db_session.add_all([prior_encounter, current_encounter])
    await db_session.flush()

    note = Note(encounter_id=prior_encounter.id)
    db_session.add(note)
    await db_session.flush()

    version = NoteVersion(
        note_id=note.id,
        version_number=1,
        saved_by_user_id=provider.id,
        assessment="Right knee osteoarthritis",
        plan="Continue physical therapy and topical diclofenac.",
    )
    db_session.add(version)
    note.current_version_id = version.id
    await db_session.commit()

    history = await PatientHistoryService().get_relevant_history(db_session, encounter=current_encounter)
    assert len(history.items) == 1
    assert "physical therapy" in history.items[0].summary.lower()


@pytest.mark.asyncio
async def test_generation_streams_structured_sections_and_saves_draft(client, db_session) -> None:
    fake_client = FakeClinicalScribeClient()

    def override_note_generation_service() -> NoteGenerationService:
        return NoteGenerationService(ai_client=fake_client, patient_history_service=PatientHistoryService())

    client._transport.app.dependency_overrides[get_note_generation_service] = override_note_generation_service

    provider = create_user("generation.provider@example.com", UserRole.PROVIDER)
    admin = create_user("generation.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    template = build_template(creator_id=admin.id)
    patient = Patient(first_name="Jordan", last_name="Knee", date_of_birth=date(1964, 3, 14))
    db_session.add_all([template, patient])
    await db_session.flush()

    prior_encounter = Encounter(
        patient_id=patient.id,
        provider_id=provider.id,
        template_id=template.id,
        status=EncounterStatus.COMPLETED,
        encounter_date=datetime.now(UTC) - timedelta(days=14),
    )
    current_encounter = Encounter(
        patient_id=patient.id,
        provider_id=provider.id,
        template_id=template.id,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime.now(UTC),
    )
    db_session.add_all([prior_encounter, current_encounter])
    await db_session.flush()

    prior_note = Note(encounter_id=prior_encounter.id)
    db_session.add(prior_note)
    await db_session.flush()
    prior_version = NoteVersion(
        note_id=prior_note.id,
        version_number=1,
        saved_by_user_id=provider.id,
        assessment="Right knee osteoarthritis",
        plan="Continue physical therapy.",
    )
    db_session.add(prior_version)
    prior_note.current_version_id = prior_version.id

    draft = EncounterDraft(
        encounter_id=current_encounter.id,
        transcript="Patient reports chronic right knee pain worsened on stairs and denies fever.",
        observations="Prior physical therapy helped slightly.",
        draft_revision=1,
    )
    db_session.add(draft)
    await db_session.commit()

    await sign_in(client, provider.email)
    response = await client.post(f"/api/encounters/{current_encounter.id}/generate")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse_events(response.text)
    event_names = [event for event, _ in events]
    assert "generation_started" in event_names
    assert "section_delta" in event_names
    assert "assessment_code" in event_names
    assert "draft_saved" in event_names
    assert "generation_complete" in event_names

    updated_draft = await db_session.scalar(
        select(EncounterDraft).where(EncounterDraft.encounter_id == current_encounter.id)
    )
    assert updated_draft is not None
    assert "denies fever" in (updated_draft.subjective or "").lower()
    assert "physical therapy" in fake_client.user_prompt.lower()
    assert "Emphasize pain duration" in fake_client.system_prompt

    client._transport.app.dependency_overrides.pop(get_note_generation_service, None)


@pytest.mark.asyncio
async def test_generation_rejects_meaningless_content(client, db_session) -> None:
    fake_client = FakeClinicalScribeClient()

    def override_note_generation_service() -> NoteGenerationService:
        return NoteGenerationService(ai_client=fake_client, patient_history_service=PatientHistoryService())

    client._transport.app.dependency_overrides[get_note_generation_service] = override_note_generation_service

    provider = create_user("meaningless.provider@example.com", UserRole.PROVIDER)
    admin = create_user("meaningless.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    template = build_template(creator_id=admin.id)
    patient = Patient(first_name="Avery", last_name="Short", date_of_birth=date(1992, 8, 7))
    db_session.add_all([template, patient])
    await db_session.flush()

    encounter = Encounter(
        patient_id=patient.id,
        provider_id=provider.id,
        template_id=template.id,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime.now(UTC),
    )
    db_session.add(encounter)
    await db_session.flush()

    draft = EncounterDraft(
        encounter_id=encounter.id,
        transcript="Hello okay thanks",
        observations="",
        draft_revision=1,
    )
    db_session.add(draft)
    await db_session.commit()

    await sign_in(client, provider.email)
    response = await client.post(f"/api/encounters/{encounter.id}/generate")

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert any(
        event == "generation_error" and data["code"] == "insufficient_clinical_content"
        for event, data in events
    )

    updated_draft = await db_session.scalar(select(EncounterDraft).where(EncounterDraft.encounter_id == encounter.id))
    assert updated_draft is not None
    assert updated_draft.subjective is None

    client._transport.app.dependency_overrides.pop(get_note_generation_service, None)


@pytest.mark.asyncio
async def test_generation_ai_provider_failure_preserves_existing_draft(client, db_session) -> None:
    failing_client = FailingClinicalScribeClient()

    def override_note_generation_service() -> NoteGenerationService:
        return NoteGenerationService(
            ai_client=failing_client,
            patient_history_service=PatientHistoryService(),
        )

    client._transport.app.dependency_overrides[get_note_generation_service] = override_note_generation_service

    provider = create_user("generation.failure.provider@example.com", UserRole.PROVIDER)
    admin = create_user("generation.failure.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    template = build_template(creator_id=admin.id)
    patient = Patient(first_name="Riley", last_name="Retry", date_of_birth=date(1991, 5, 17))
    db_session.add_all([template, patient])
    await db_session.flush()

    encounter = Encounter(
        patient_id=patient.id,
        provider_id=provider.id,
        template_id=template.id,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime.now(UTC),
    )
    db_session.add(encounter)
    await db_session.flush()

    draft = EncounterDraft(
        encounter_id=encounter.id,
        transcript="Patient reports chronic cough and denies chest pain.",
        observations="Existing manual note should remain.",
        subjective="Existing subjective content.",
        objective="Existing objective content.",
        assessment="Existing assessment content.",
        plan="Existing plan content.",
        draft_revision=4,
    )
    db_session.add(draft)
    await db_session.commit()

    await sign_in(client, provider.email)
    response = await client.post(f"/api/encounters/{encounter.id}/generate")

    assert response.status_code == 200
    events = parse_sse_events(response.text)
    assert any(
        event == "generation_error" and data["code"] == "ai_provider_error"
        for event, data in events
    )

    updated_draft = await db_session.scalar(
        select(EncounterDraft).where(EncounterDraft.encounter_id == encounter.id)
    )
    assert updated_draft is not None
    assert updated_draft.subjective == "Existing subjective content."
    assert updated_draft.objective == "Existing objective content."
    assert updated_draft.assessment == "Existing assessment content."
    assert updated_draft.plan == "Existing plan content."
    assert updated_draft.draft_revision == 4

    client._transport.app.dependency_overrides.pop(get_note_generation_service, None)
