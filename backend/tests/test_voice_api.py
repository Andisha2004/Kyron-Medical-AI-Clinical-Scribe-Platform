from datetime import UTC, date, datetime

import pytest

from app.core.security import hash_password
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus, UserRole
from app.db.models.patient import Patient
from app.db.models.template import Template
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


async def setup_voice_encounter(db_session):
    admin = create_user("voice-admin@example.com", UserRole.ADMIN)
    provider = create_user("voice-provider@example.com", UserRole.PROVIDER)
    patient = Patient(first_name="Jordan", last_name="Voice", date_of_birth=date(1990, 1, 1))
    template = Template(
        name="Voice Template",
        description="Voice editing test template.",
        is_active=True,
        created_by_user=admin,
    )
    encounter = Encounter(
        patient=patient,
        provider=provider,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
    )
    draft = EncounterDraft(
        encounter=encounter,
        transcript="Patient reports knee pain.",
        subjective="Patient reports knee pain.",
        objective="Mild swelling noted.",
        assessment="Knee pain.",
        plan="Continue medication instructions. Follow up in four weeks. Return earlier if worse.",
        selected_icd10_codes=[],
        draft_revision=1,
    )
    db_session.add_all([admin, provider, patient, template, encounter, draft])
    await db_session.commit()
    return provider, encounter, draft


@pytest.mark.asyncio
async def test_voice_session_endpoint_returns_provider_capabilities(client, db_session):
    provider, encounter, _ = await setup_voice_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(f"/api/voice/encounters/{encounter.id}/session")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "openai_realtime"
    assert payload["supports_interruption"] is True
    assert payload["supports_tool_calls"] is True
    assert payload["supports_continuous_conversation"] is True


@pytest.mark.asyncio
async def test_voice_command_append_updates_subjective(client, db_session):
    provider, encounter, _ = await setup_voice_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(
        f"/api/voice/encounters/{encounter.id}/commands",
        json={"command": "Add that the patient denies fever.", "base_revision": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["operation"]["operation"] == "append"
    assert payload["updated_section"] == "subjective"
    assert "Patient denies fever." in payload["draft"]["subjective"]
    assert payload["draft_revision"] == 2


@pytest.mark.asyncio
async def test_voice_command_move_moves_content_between_sections(client, db_session):
    provider, encounter, draft = await setup_voice_encounter(db_session)
    draft.objective = "Knee pain. Mild swelling noted."
    draft.subjective = "Patient follow-up."
    await db_session.commit()

    await sign_in(client, provider.email)
    response = await client.post(
        f"/api/voice/encounters/{encounter.id}/commands",
        json={"command": "Move knee pain into Subjective.", "base_revision": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Knee pain" in payload["draft"]["subjective"]
    assert "Knee pain" not in payload["draft"]["objective"]


@pytest.mark.asyncio
async def test_voice_command_remove_sentence_by_keyword(client, db_session):
    provider, encounter, _ = await setup_voice_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(
        f"/api/voice/encounters/{encounter.id}/commands",
        json={"command": "Remove the sentence about swelling.", "base_revision": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "swelling" not in (payload["draft"]["objective"] or "").lower()


@pytest.mark.asyncio
async def test_voice_command_shorten_plan(client, db_session):
    provider, encounter, _ = await setup_voice_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(
        f"/api/voice/encounters/{encounter.id}/commands",
        json={"command": "Shorten the Plan", "base_revision": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    original_length = len(
        "Continue medication instructions. Follow up in four weeks. Return earlier if worse."
    )
    assert len(payload["draft"]["plan"]) < original_length
    assert payload["assistant_response"] == "I shortened Plan."


@pytest.mark.asyncio
async def test_voice_command_adds_assessment_item(client, db_session):
    provider, encounter, _ = await setup_voice_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(
        f"/api/voice/encounters/{encounter.id}/commands",
        json={"command": "Add osteoarthritis to Assessment.", "base_revision": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["updated_section"] == "assessment"
    assert "Osteoarthritis." in payload["draft"]["assessment"]


@pytest.mark.asyncio
async def test_voice_command_rejects_ambiguous_or_unsupported_requests(client, db_session):
    provider, encounter, _ = await setup_voice_encounter(db_session)
    await sign_in(client, provider.email)

    ambiguous_response = await client.post(
        f"/api/voice/encounters/{encounter.id}/commands",
        json={"command": "Remove that", "base_revision": 1},
    )
    assert ambiguous_response.status_code == 422

    unsupported_response = await client.post(
        f"/api/voice/encounters/{encounter.id}/commands",
        json={"command": "Translate this note to Spanish", "base_revision": 1},
    )
    assert unsupported_response.status_code == 422

    rewrite_response = await client.post(
        f"/api/voice/encounters/{encounter.id}/commands",
        json={"command": "Add all the notes to the SOAP notes and make it better", "base_revision": 1},
    )
    assert rewrite_response.status_code == 422
