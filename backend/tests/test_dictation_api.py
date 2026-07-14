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


async def setup_dictation_encounter(db_session):
    admin = create_user("dictation-admin@example.com", UserRole.ADMIN)
    provider = create_user("dictation-provider@example.com", UserRole.PROVIDER)
    patient = Patient(first_name="Jordan", last_name="Dictation", date_of_birth=date(1992, 2, 2))
    template = Template(
        name="Dictation Template",
        description="Dictation testing template.",
        is_active=True,
        created_by_user=admin,
    )
    encounter = Encounter(
        patient=patient,
        provider=provider,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 14, 11, 0, tzinfo=UTC),
    )
    draft = EncounterDraft(
        encounter=encounter,
        transcript="",
        observations="",
        subjective="",
        objective="",
        assessment="",
        plan="",
        selected_icd10_codes=[],
        draft_revision=1,
    )
    db_session.add_all([admin, provider, patient, template, encounter, draft])
    await db_session.commit()
    return provider, encounter


@pytest.mark.asyncio
async def test_dictation_session_endpoint_reports_realtime_provider(client, db_session):
    provider, encounter = await setup_dictation_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(f"/api/voice/encounters/{encounter.id}/dictation/session")

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "openai_realtime"
    assert payload["model"] == "gpt-realtime-whisper"
    assert payload["supports_partial_transcripts"] is True
    assert payload["supports_final_transcripts"] is True


@pytest.mark.asyncio
async def test_partial_dictation_segment_does_not_save_note_changes(client, db_session):
    provider, encounter = await setup_dictation_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(
        f"/api/voice/encounters/{encounter.id}/dictation/segments",
        json={
            "transcript_segment": "patient reports",
            "is_final": False,
            "base_revision": 1,
            "segment_id": "partial-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["transcript_appended"] is False
    assert payload["partial_transcript"] == "patient reports"
    assert payload["operations"] == []
    assert payload["draft_revision"] == 1


@pytest.mark.asyncio
async def test_final_dictation_segment_appends_transcript_and_updates_subjective(client, db_session):
    provider, encounter = await setup_dictation_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(
        f"/api/voice/encounters/{encounter.id}/dictation/segments",
        json={
            "transcript_segment": "Patient denies fever or chills.",
            "is_final": True,
            "base_revision": 1,
            "segment_id": "final-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript_appended"] is True
    assert payload["operations"][0]["section"] == "subjective"
    assert "Patient denies fever or chills." in payload["draft"]["transcript"]
    assert "Patient denies fever or chills." in payload["draft"]["subjective"]
    assert payload["draft_revision"] == 2


@pytest.mark.asyncio
async def test_final_dictation_segment_updates_plan_when_follow_up_language_present(client, db_session):
    provider, encounter = await setup_dictation_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(
        f"/api/voice/encounters/{encounter.id}/dictation/segments",
        json={
            "transcript_segment": "Continue physical therapy and follow up in four weeks.",
            "is_final": True,
            "base_revision": 1,
            "segment_id": "plan-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["operations"][0]["section"] == "plan"
    assert "Continue physical therapy and follow up in four weeks." in payload["draft"]["plan"]


@pytest.mark.asyncio
async def test_duplicate_final_segment_is_not_appended_twice(client, db_session):
    provider, encounter = await setup_dictation_encounter(db_session)
    await sign_in(client, provider.email)

    first_response = await client.post(
        f"/api/voice/encounters/{encounter.id}/dictation/segments",
        json={
            "transcript_segment": "Patient reports cough for three days.",
            "is_final": True,
            "base_revision": 1,
            "segment_id": "dup-1",
        },
    )
    assert first_response.status_code == 200

    second_response = await client.post(
        f"/api/voice/encounters/{encounter.id}/dictation/segments",
        json={
            "transcript_segment": "Patient reports cough for three days.",
            "is_final": True,
            "base_revision": 2,
            "segment_id": "dup-2",
        },
    )
    assert second_response.status_code == 200
    payload = second_response.json()
    assert payload["transcript_appended"] is False
    assert payload["operations"] == []


@pytest.mark.asyncio
async def test_dictation_segment_rejects_stale_revision(client, db_session):
    provider, encounter = await setup_dictation_encounter(db_session)
    await sign_in(client, provider.email)

    response = await client.post(
        f"/api/voice/encounters/{encounter.id}/dictation/segments",
        json={
            "transcript_segment": "Patient reports cough.",
            "is_final": True,
            "base_revision": 99,
            "segment_id": "stale-1",
        },
    )

    assert response.status_code == 409
