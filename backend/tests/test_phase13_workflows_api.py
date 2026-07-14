from datetime import UTC, date, datetime, timedelta
import json

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.db.models.audit_log import AuditLog
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus, TemplateSectionType, UserRole
from app.db.models.icd10_code import Icd10Code
from app.db.models.note import Note
from app.db.models.note_version import NoteVersion
from app.db.models.patient import Patient
from app.db.models.provider_profile import ProviderProfile
from app.db.models.template import Template
from app.db.models.template_section import TemplateSection
from app.db.models.user import User
from app.schemas.generation import AssessmentItem, SoapNoteGenerationResult
from app.services.note_generation_service import NoteGenerationService, get_note_generation_service
from app.services.patient_history_service import PatientHistoryService


class CapturingClinicalScribeClient:
    def __init__(self) -> None:
        self.system_prompt: str | None = None
        self.user_prompt: str | None = None

    async def generate_soap_note(self, *, system_prompt: str, user_prompt: str) -> SoapNoteGenerationResult:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        history_suffix = ""
        if "physical therapy" in user_prompt.lower():
            history_suffix = " Returning after physical therapy with partial improvement."

        return SoapNoteGenerationResult(
            subjective=f"Patient reports chronic right knee pain on stairs.{history_suffix}",
            objective="No objective examination findings were documented.",
            assessment=[
                AssessmentItem(
                    diagnosis="Right knee osteoarthritis",
                    icd10_code="M17.11",
                    description="Unilateral primary osteoarthritis, right knee",
                )
            ],
            plan="Continue physical therapy and follow up in four weeks.",
            missing_information=[],
            warnings=[],
        )


def create_user(email: str, role: UserRole, *, password: str = "DemoPass123!") -> User:
    return User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )


async def sign_in(client, email: str, password: str = "DemoPass123!") -> None:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def build_template(*, creator_id: str, name: str = "Orthopedic Follow-Up") -> Template:
    template = Template(
        name=name,
        description="Structured follow-up template.",
        is_active=True,
        created_by_user_id=creator_id,
    )
    template.sections = [
        TemplateSection(
            section=TemplateSectionType.SUBJECTIVE,
            instructions="Capture symptom history first.",
            sort_order=1,
        ),
        TemplateSection(
            section=TemplateSectionType.OBJECTIVE,
            instructions="Only include documented exam findings.",
            sort_order=2,
        ),
        TemplateSection(
            section=TemplateSectionType.ASSESSMENT,
            instructions="Suggest reviewable diagnoses and ICD-10 codes.",
            sort_order=3,
        ),
        TemplateSection(
            section=TemplateSectionType.PLAN,
            instructions="State follow-up, treatment, and monitoring clearly.",
            sort_order=4,
        ),
    ]
    return template


def parse_sse_events(raw_text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in raw_text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_name = ""
        data: dict = {}
        for line in block.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        if event_name:
            events.append((event_name, data))
    return events


@pytest.mark.asyncio
async def test_core_provider_workflow_end_to_end(client, db_session) -> None:
    fake_client = CapturingClinicalScribeClient()

    def override_note_generation_service() -> NoteGenerationService:
        return NoteGenerationService(ai_client=fake_client, patient_history_service=PatientHistoryService())

    client._transport.app.dependency_overrides[get_note_generation_service] = (
        override_note_generation_service
    )

    provider = create_user("phase13.provider@example.com", UserRole.PROVIDER)
    admin = create_user("phase13.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    db_session.add(
        ProviderProfile(
            user_id=provider.id,
            first_name="Maya",
            last_name="Chen",
            specialty="Family Medicine",
        )
    )

    template = build_template(creator_id=admin.id)
    icd_code = Icd10Code(
        code="M17.11",
        description="Unilateral primary osteoarthritis, right knee",
        category="Orthopedic",
        search_text="right knee osteoarthritis degenerative joint pain",
    )
    db_session.add_all([template, icd_code])
    await db_session.commit()

    await sign_in(client, provider.email)

    create_response = await client.post(
        "/api/encounters",
        json={
            "first_name": "Jordan",
            "last_name": "Walker",
            "date_of_birth": "1975-06-15",
            "template_id": template.id,
        },
    )
    assert create_response.status_code == 201
    encounter_id = create_response.json()["encounter_id"]

    update_response = await client.patch(
        f"/api/encounters/{encounter_id}/draft",
        json={
            "base_revision": 1,
            "transcript": "Patient reports chronic right knee pain on stairs and denies fever.",
            "observations": "No exam findings documented yet.",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["draft_revision"] == 2

    generate_response = await client.post(f"/api/encounters/{encounter_id}/generate")
    assert generate_response.status_code == 200
    events = parse_sse_events(generate_response.text)
    event_names = [name for name, _ in events]
    assert "generation_started" in event_names
    assert "section_delta" in event_names
    assert "assessment_code" in event_names
    assert event_names[-1] == "generation_complete"

    icd_response = await client.get("/api/icd/search", params={"q": "right knee osteoarthritis"})
    assert icd_response.status_code == 200
    assert icd_response.json()[0]["code"] == "M17.11"

    save_response = await client.post(
        f"/api/encounters/{encounter_id}/save",
        json={
            "subjective": "Patient reports chronic right knee pain on stairs.",
            "objective": "No objective examination findings were documented.",
            "assessment": "1. Right knee osteoarthritis — ICD-10: M17.11",
            "plan": "Continue physical therapy and follow up in four weeks.",
            "icd10_codes": [
                {
                    "code": "M17.11",
                    "description": "Unilateral primary osteoarthritis, right knee",
                }
            ],
            "idempotency_key": "phase13-core-workflow-001",
            "generation_metadata": {"source": "phase13-e2e"},
        },
    )
    assert save_response.status_code == 200
    save_payload = save_response.json()

    encounter_response = await client.get(f"/api/encounters/{encounter_id}")
    assert encounter_response.status_code == 200
    encounter_payload = encounter_response.json()
    assert encounter_payload["note_id"] == save_payload["note_id"]
    assert encounter_payload["draft"]["subjective"].startswith("Patient reports chronic right knee pain")
    assert encounter_payload["versions"][0]["version_number"] == 1

    versions_response = await client.get(f"/api/notes/{save_payload['note_id']}/versions")
    assert versions_response.status_code == 200
    versions = versions_response.json()
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["icd10_codes"][0]["code"] == "M17.11"


@pytest.mark.asyncio
async def test_returning_patient_generation_includes_relevant_history(client, db_session) -> None:
    fake_client = CapturingClinicalScribeClient()

    def override_note_generation_service() -> NoteGenerationService:
        return NoteGenerationService(ai_client=fake_client, patient_history_service=PatientHistoryService())

    client._transport.app.dependency_overrides[get_note_generation_service] = (
        override_note_generation_service
    )

    provider = create_user("phase13.returning.provider@example.com", UserRole.PROVIDER)
    admin = create_user("phase13.returning.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    template = build_template(creator_id=admin.id, name="Returning Patient Template")
    patient = Patient(first_name="Jordan", last_name="History", date_of_birth=date(1980, 8, 20))
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

    db_session.add(
        EncounterDraft(
            encounter_id=current_encounter.id,
            transcript="Patient reports chronic right knee pain on stairs.",
            observations="No exam findings documented yet.",
            draft_revision=1,
        )
    )

    note = Note(encounter_id=prior_encounter.id)
    db_session.add(note)
    await db_session.flush()
    version = NoteVersion(
        note_id=note.id,
        version_number=1,
        saved_by_user_id=provider.id,
        assessment="Right knee osteoarthritis",
        plan="Continue physical therapy and home exercises.",
    )
    db_session.add(version)
    note.current_version_id = version.id
    await db_session.commit()

    await sign_in(client, provider.email)
    generate_response = await client.post(f"/api/encounters/{current_encounter.id}/generate")
    assert generate_response.status_code == 200
    events = parse_sse_events(generate_response.text)

    subjective_text = "".join(
        event_data["text"]
        for event_name, event_data in events
        if event_name == "section_delta" and event_data["section"] == "subjective"
    )
    assert "physical therapy" in subjective_text.lower()
    assert fake_client.user_prompt is not None
    assert "physical therapy" in fake_client.user_prompt.lower()


@pytest.mark.asyncio
async def test_admin_workflow_updates_template_and_provider_uses_latest_instructions(client, db_session) -> None:
    fake_client = CapturingClinicalScribeClient()

    def override_note_generation_service() -> NoteGenerationService:
        return NoteGenerationService(ai_client=fake_client, patient_history_service=PatientHistoryService())

    client._transport.app.dependency_overrides[get_note_generation_service] = (
        override_note_generation_service
    )

    admin = create_user("phase13.workflow.admin@example.com", UserRole.ADMIN)
    db_session.add(admin)
    await db_session.commit()

    await sign_in(client, admin.email)

    create_provider_response = await client.post(
        "/api/admin/providers",
        json={
            "first_name": "Alicia",
            "last_name": "Wright",
            "email": "phase13.workflow.provider@example.com",
            "password": "DemoPass123!",
            "specialty": "Orthopedics",
        },
    )
    assert create_provider_response.status_code == 201
    provider_id = create_provider_response.json()["id"]

    create_template_response = await client.post(
        "/api/admin/templates",
        json={
            "name": "Live Update Template",
            "description": "Template before admin update",
            "is_active": True,
            "sections": [
                {"section": "subjective", "instructions": "Original subjective guidance", "sort_order": 1},
                {"section": "objective", "instructions": "Original objective guidance", "sort_order": 2},
                {"section": "assessment", "instructions": "Original assessment guidance", "sort_order": 3},
                {"section": "plan", "instructions": "Original plan guidance", "sort_order": 4},
            ],
        },
    )
    assert create_template_response.status_code == 201
    template_id = create_template_response.json()["id"]

    deactivate_response = await client.patch(
        f"/api/admin/providers/{provider_id}/status",
        json={"is_active": False},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    reactivate_response = await client.patch(
        f"/api/admin/providers/{provider_id}/status",
        json={"is_active": True},
    )
    assert reactivate_response.status_code == 200
    assert reactivate_response.json()["is_active"] is True

    update_template_response = await client.put(
        f"/api/admin/templates/{template_id}",
        json={
            "name": "Live Update Template",
            "description": "Template after admin update",
            "is_active": True,
            "sections": [
                {"section": "subjective", "instructions": "Updated subjective guidance", "sort_order": 1},
                {"section": "objective", "instructions": "Updated objective guidance", "sort_order": 2},
                {"section": "assessment", "instructions": "Updated assessment guidance", "sort_order": 3},
                {"section": "plan", "instructions": "Updated plan guidance", "sort_order": 4},
            ],
        },
    )
    assert update_template_response.status_code == 200

    provider_login_response = await client.post(
        "/api/auth/login",
        json={"email": "phase13.workflow.provider@example.com", "password": "DemoPass123!"},
    )
    assert provider_login_response.status_code == 200

    create_encounter_response = await client.post(
        "/api/encounters",
        json={
            "first_name": "Jamie",
            "last_name": "Template",
            "date_of_birth": "1992-02-02",
            "template_id": template_id,
        },
    )
    assert create_encounter_response.status_code == 201
    encounter_id = create_encounter_response.json()["encounter_id"]

    update_draft_response = await client.patch(
        f"/api/encounters/{encounter_id}/draft",
        json={
            "base_revision": 1,
            "transcript": "Patient reports chronic right knee pain on stairs and denies fever.",
            "observations": "No exam findings documented yet.",
        },
    )
    assert update_draft_response.status_code == 200

    generate_response = await client.post(f"/api/encounters/{encounter_id}/generate")
    assert generate_response.status_code == 200
    assert "generation_complete" in [event for event, _ in parse_sse_events(generate_response.text)]
    assert fake_client.system_prompt is not None
    assert "Updated subjective guidance" in fake_client.system_prompt
    assert "Updated plan guidance" in fake_client.system_prompt

    audit_actions = (
        await db_session.scalars(
            select(AuditLog.action).where(
                AuditLog.action.in_(
                    [
                        "PROVIDER_CREATED",
                        "PROVIDER_DEACTIVATED",
                        "PROVIDER_REACTIVATED",
                        "TEMPLATE_UPDATED",
                    ]
                )
            )
        )
    ).all()
    assert "PROVIDER_CREATED" in audit_actions
    assert "PROVIDER_DEACTIVATED" in audit_actions
    assert "PROVIDER_REACTIVATED" in audit_actions
    assert "TEMPLATE_UPDATED" in audit_actions
