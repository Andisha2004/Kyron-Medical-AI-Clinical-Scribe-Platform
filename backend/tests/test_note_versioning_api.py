from datetime import UTC, date, datetime

import pytest

from app.core.security import hash_password
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus, TemplateSectionType, UserRole
from app.db.models.template import Template
from app.db.models.template_section import TemplateSection
from app.db.models.patient import Patient
from app.db.models.provider_profile import ProviderProfile
from app.db.models.user import User


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
        name="General Follow-Up",
        description="General clinical follow-up template",
        is_active=True,
        created_by_user_id=creator_id,
    )
    template.sections = [
        TemplateSection(
            section=TemplateSectionType.SUBJECTIVE,
            instructions="Subjective guidance",
            sort_order=1,
        ),
        TemplateSection(
            section=TemplateSectionType.OBJECTIVE,
            instructions="Objective guidance",
            sort_order=2,
        ),
    ]
    return template


@pytest.mark.asyncio
async def test_save_note_is_idempotent_for_duplicate_request_key(client, db_session) -> None:
    provider = create_user("versioning.provider@example.com", UserRole.PROVIDER)
    admin = create_user("versioning.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    db_session.add(
        ProviderProfile(
            user_id=provider.id,
            first_name="Maya",
            last_name="Chen",
            specialty="Internal Medicine",
        )
    )

    template = build_template(creator_id=admin.id)
    patient = Patient(first_name="Jordan", last_name="Retry", date_of_birth=date(1990, 1, 1))
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
        subjective="Initial subjective",
        objective="Initial objective",
        assessment="Initial assessment",
        plan="Initial plan",
    )
    db_session.add(draft)
    await db_session.commit()

    await sign_in(client, provider.email)
    payload = {
        "subjective": "Patient reports chronic right knee pain.",
        "objective": "No exam findings were documented.",
        "assessment": "1. Right knee pain",
        "plan": "Follow up in two weeks.",
        "icd10_codes": [],
        "idempotency_key": "save-request-001",
        "generation_metadata": {"source": "phase6_test"},
    }

    first_response = await client.post(f"/api/encounters/{encounter.id}/save", json=payload)
    second_response = await client.post(f"/api/encounters/{encounter.id}/save", json=payload)

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["version_id"] == second_response.json()["version_id"]
    assert first_response.json()["version_number"] == 1
    assert second_response.json()["version_number"] == 1


@pytest.mark.asyncio
async def test_versions_api_returns_newest_first_and_preserves_original_content(client, db_session) -> None:
    provider = create_user("versions.history.provider@example.com", UserRole.PROVIDER)
    admin = create_user("versions.history.admin@example.com", UserRole.ADMIN)
    db_session.add_all([provider, admin])
    await db_session.flush()

    db_session.add(
        ProviderProfile(
            user_id=provider.id,
            first_name="Maya",
            last_name="Chen",
            specialty="Internal Medicine",
        )
    )

    template = build_template(creator_id=admin.id)
    patient = Patient(first_name="Jordan", last_name="History", date_of_birth=date(1988, 5, 10))
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

    db_session.add(EncounterDraft(encounter_id=encounter.id))
    await db_session.commit()

    await sign_in(client, provider.email)
    first_save = await client.post(
        f"/api/encounters/{encounter.id}/save",
        json={
            "subjective": "Version one subjective",
            "objective": "Version one objective",
            "assessment": "Version one assessment",
            "plan": "Version one plan",
            "icd10_codes": [{"code": "M25.561", "description": "Pain in right knee"}],
            "idempotency_key": "save-request-101",
            "generation_metadata": {"source": "phase6_test"},
        },
    )
    assert first_save.status_code == 200

    second_save = await client.post(
        f"/api/encounters/{encounter.id}/save",
        json={
            "subjective": "Version two subjective",
            "objective": "Version two objective",
            "assessment": "Version two assessment",
            "plan": "Version two plan",
            "icd10_codes": [{"code": "M25.561", "description": "Pain in right knee"}],
            "idempotency_key": "save-request-102",
            "generation_metadata": {"source": "phase6_test"},
        },
    )
    assert second_save.status_code == 200

    note_id = second_save.json()["note_id"]
    versions_response = await client.get(f"/api/notes/{note_id}/versions")

    assert versions_response.status_code == 200
    versions = versions_response.json()
    assert [version["version_number"] for version in versions] == [2, 1]
    assert versions[0]["subjective"] == "Version two subjective"
    assert versions[1]["subjective"] == "Version one subjective"
    assert versions[0]["saved_by_user"]["first_name"] == "Maya"
    assert versions[0]["saved_by_user"]["last_name"] == "Chen"
