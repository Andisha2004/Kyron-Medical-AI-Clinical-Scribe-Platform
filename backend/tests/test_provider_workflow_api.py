from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus, TemplateSectionType, UserRole
from app.db.models.patient import Patient
from app.db.models.provider_profile import ProviderProfile
from app.db.models.template import Template
from app.db.models.template_section import TemplateSection
from app.db.models.user import User


def create_user(email: str, role: UserRole) -> User:
    return User(
        email=email,
        password_hash=hash_password("password123"),
        role=role,
        is_active=True,
    )


async def sign_in(client, email: str, password: str = "password123") -> None:
    response = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200


def create_template(*, creator_id: str, name: str = "Orthopedic Follow-Up") -> Template:
    template = Template(
        name=name,
        description="Focused follow-up template.",
        is_active=True,
        created_by_user_id=creator_id,
    )
    template.sections = [
        TemplateSection(
            section=TemplateSectionType.SUBJECTIVE,
            instructions="Capture symptoms and progression.",
            sort_order=1,
        ),
        TemplateSection(
            section=TemplateSectionType.OBJECTIVE,
            instructions="Capture exam findings.",
            sort_order=2,
        ),
    ]
    return template


@pytest.mark.asyncio
async def test_provider_dashboard_returns_only_current_provider_encounters(client, db_session):
    provider_one = create_user("phase4.provider.one@example.com", UserRole.PROVIDER)
    provider_two = create_user("phase4.provider.two@example.com", UserRole.PROVIDER)
    admin = create_user("phase4.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider_one, provider_two, admin])
    await db_session.flush()

    db_session.add(
        ProviderProfile(
            user_id=provider_one.id,
            first_name="Avery",
            last_name="Stone",
            specialty="Family Medicine",
        )
    )
    template = create_template(creator_id=admin.id)
    db_session.add(template)
    await db_session.flush()

    patient_one = Patient(first_name="Jordan", last_name="Test", date_of_birth=date(1990, 1, 1))
    patient_two = Patient(first_name="Taylor", last_name="Example", date_of_birth=date(1988, 5, 17))
    db_session.add_all([patient_one, patient_two])
    await db_session.flush()

    older_encounter = Encounter(
        patient_id=patient_one.id,
        provider_id=provider_one.id,
        template_id=template.id,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime.now(UTC) - timedelta(days=2),
    )
    newer_encounter = Encounter(
        patient_id=patient_two.id,
        provider_id=provider_one.id,
        template_id=template.id,
        status=EncounterStatus.COMPLETED,
        encounter_date=datetime.now(UTC) - timedelta(days=1),
    )
    other_provider_encounter = Encounter(
        patient_id=patient_one.id,
        provider_id=provider_two.id,
        template_id=template.id,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime.now(UTC),
    )
    db_session.add_all([older_encounter, newer_encounter, other_provider_encounter])
    await db_session.flush()

    older_encounter.updated_at = datetime.now(UTC) - timedelta(hours=5)
    newer_encounter.updated_at = datetime.now(UTC) - timedelta(hours=1)
    other_provider_encounter.updated_at = datetime.now(UTC)
    await db_session.commit()

    await sign_in(client, provider_one.email)
    response = await client.get("/api/encounters")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_name"] == "Avery Stone"
    assert payload["draft_count"] == 1
    assert payload["completed_count"] == 1
    assert [item["id"] for item in payload["encounters"]] == [newer_encounter.id, older_encounter.id]
    assert all(item["patient_name"] in {"Jordan Test", "Taylor Example"} for item in payload["encounters"])


@pytest.mark.asyncio
async def test_create_encounter_reuses_existing_patient_and_creates_empty_draft(client, db_session):
    provider = create_user("phase4.reuse.provider@example.com", UserRole.PROVIDER)
    admin = create_user("phase4.reuse.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    template = create_template(creator_id=admin.id, name="Urgent Care Visit")
    db_session.add(template)
    patient = Patient(first_name="Jordan", last_name="Test", date_of_birth=date(1990, 1, 1))
    db_session.add(patient)
    await db_session.flush()

    prior_encounter = Encounter(
        patient_id=patient.id,
        provider_id=provider.id,
        template_id=template.id,
        status=EncounterStatus.COMPLETED,
        encounter_date=datetime.now(UTC) - timedelta(days=10),
    )
    db_session.add(prior_encounter)
    await db_session.commit()

    await sign_in(client, provider.email)
    response = await client.post(
        "/api/encounters",
        json={
            "first_name": "Jordan",
            "last_name": "Test",
            "date_of_birth": "1990-01-01",
            "template_id": template.id,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["patient_id"] == patient.id
    assert payload["reused_existing_patient"] is True
    assert payload["has_prior_history"] is True
    assert payload["prior_encounter_count"] == 1

    draft = await db_session.scalar(
        select(EncounterDraft).where(EncounterDraft.encounter_id == payload["encounter_id"])
    )
    assert draft is not None
    assert draft.draft_revision == 1
    assert draft.transcript is None


@pytest.mark.asyncio
async def test_create_encounter_creates_new_patient_when_no_match_exists(client, db_session):
    provider = create_user("phase4.new.provider@example.com", UserRole.PROVIDER)
    admin = create_user("phase4.new.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    template = create_template(creator_id=admin.id, name="New Patient Evaluation")
    db_session.add(template)
    await db_session.commit()

    await sign_in(client, provider.email)
    response = await client.post(
        "/api/encounters",
        json={
            "first_name": "Morgan",
            "last_name": "Rivera",
            "date_of_birth": "1994-06-15",
            "template_id": template.id,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["reused_existing_patient"] is False
    assert payload["has_prior_history"] is False
    assert payload["prior_encounter_count"] == 0

    created_patient = await db_session.get(Patient, payload["patient_id"])
    assert created_patient is not None
    assert created_patient.first_name == "Morgan"
    assert created_patient.last_name == "Rivera"


@pytest.mark.asyncio
async def test_draft_conflict_returns_latest_revision_and_preserves_server_state(client, db_session):
    provider = create_user("phase4.conflict.provider@example.com", UserRole.PROVIDER)
    admin = create_user("phase4.conflict.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    template = create_template(creator_id=admin.id)
    patient = Patient(first_name="Jordan", last_name="Conflict", date_of_birth=date(1991, 2, 10))
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
        transcript="Existing transcript",
        subjective="Existing subjective",
        draft_revision=2,
    )
    db_session.add(draft)
    await db_session.commit()

    await sign_in(client, provider.email)
    response = await client.patch(
        f"/api/encounters/{encounter.id}/draft",
        json={
            "base_revision": 1,
            "transcript": "Stale client update",
            "subjective": "Should not overwrite",
        },
    )

    assert response.status_code == 409
    payload = response.json()
    assert payload["detail"] == "Draft revision conflict."
    assert payload["errors"]["latest_draft"]["draft_revision"] == 2
    assert payload["errors"]["latest_draft"]["transcript"] == "Existing transcript"

    await db_session.refresh(draft)
    assert draft.transcript == "Existing transcript"
    assert draft.subjective == "Existing subjective"
