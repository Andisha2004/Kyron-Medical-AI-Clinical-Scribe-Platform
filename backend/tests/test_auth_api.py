from datetime import UTC, datetime

import pytest

from app.core.security import hash_password, verify_password
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus, UserRole
from app.db.models.note import Note
from app.db.models.patient import Patient
from app.db.models.template import Template
from app.db.models.user import User


def create_user(email: str, role: UserRole, *, is_active: bool = True) -> User:
    return User(
        email=email,
        password_hash=hash_password("DemoPass123!"),
        role=role,
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_password_hashing_and_verification() -> None:
    hashed = hash_password("DemoPass123!")

    assert hashed != "DemoPass123!"
    assert verify_password("DemoPass123!", hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.asyncio
async def test_valid_provider_login_succeeds(client, db_session) -> None:
    provider = create_user("provider1@example.com", UserRole.PROVIDER)
    db_session.add(provider)
    await db_session.commit()

    response = await client.post(
        "/api/auth/login",
        json={"email": "PROVIDER1@example.com", "password": "DemoPass123!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "provider1@example.com"
    assert body["user"]["role"] == "provider"
    assert "password_hash" not in body["user"]
    assert "httponly" in response.headers["set-cookie"].lower()


@pytest.mark.asyncio
async def test_valid_admin_login_succeeds(client, db_session) -> None:
    admin = create_user("admin1@example.com", UserRole.ADMIN)
    db_session.add(admin)
    await db_session.commit()

    response = await client.post(
        "/api/auth/login",
        json={"email": "admin1@example.com", "password": "DemoPass123!"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "admin"


@pytest.mark.asyncio
async def test_wrong_password_returns_generic_error(client, db_session) -> None:
    provider = create_user("provider2@example.com", UserRole.PROVIDER)
    db_session.add(provider)
    await db_session.commit()

    response = await client.post(
        "/api/auth/login",
        json={"email": "provider2@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_unknown_email_returns_generic_error(client) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": "missing@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_deactivated_user_fails_login(client, db_session) -> None:
    provider = create_user("inactive@example.com", UserRole.PROVIDER, is_active=False)
    db_session.add(provider)
    await db_session.commit()

    response = await client.post(
        "/api/auth/login",
        json={"email": "inactive@example.com", "password": "DemoPass123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account is deactivated."


@pytest.mark.asyncio
async def test_current_user_endpoint_returns_safe_user_information(client, db_session) -> None:
    provider = create_user("me@example.com", UserRole.PROVIDER)
    db_session.add(provider)
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "me@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    me_response = await client.get("/api/auth/me")
    assert me_response.status_code == 200
    body = me_response.json()
    assert body["email"] == "me@example.com"
    assert body["role"] == "provider"
    assert body["is_active"] is True
    assert "password_hash" not in body


@pytest.mark.asyncio
async def test_logout_clears_authentication_cookie(client, db_session) -> None:
    provider = create_user("logout@example.com", UserRole.PROVIDER)
    db_session.add(provider)
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "logout@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    logout_response = await client.post("/api/auth/logout")
    assert logout_response.status_code == 200
    assert "max-age=0" in logout_response.headers["set-cookie"].lower()


@pytest.mark.asyncio
async def test_unauthenticated_user_cannot_access_admin_route(client) -> None:
    response = await client.get("/api/admin/providers/status")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_provider_cannot_access_admin_route(client, db_session) -> None:
    provider = create_user("provider-admin-block@example.com", UserRole.PROVIDER)
    db_session.add(provider)
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "provider-admin-block@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.get("/api/admin/providers/status")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_admin_route(client, db_session) -> None:
    admin = create_user("admin-route@example.com", UserRole.ADMIN)
    db_session.add(admin)
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "admin-route@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.get("/api/admin/providers/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_provider_one_cannot_access_provider_two_encounter(client, db_session) -> None:
    admin = create_user("encounter-admin@example.com", UserRole.ADMIN)
    provider_one = create_user("provider-one@example.com", UserRole.PROVIDER)
    provider_two = create_user("provider-two@example.com", UserRole.PROVIDER)
    patient = Patient(first_name="Jordan", last_name="Miles", date_of_birth=datetime(1990, 1, 1).date())
    template = Template(
        name="Ownership Template",
        description="Used for encounter ownership tests.",
        is_active=True,
        created_by_user=admin,
    )
    encounter = Encounter(
        patient=patient,
        provider=provider_two,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 13, 10, 0, tzinfo=UTC),
    )
    db_session.add_all([admin, provider_one, provider_two, patient, template, encounter])
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "provider-one@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.get(f"/api/encounters/{encounter.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_provider_one_cannot_update_provider_two_draft(client, db_session) -> None:
    admin = create_user("draft-admin@example.com", UserRole.ADMIN)
    provider_one = create_user("draft-provider-one@example.com", UserRole.PROVIDER)
    provider_two = create_user("draft-provider-two@example.com", UserRole.PROVIDER)
    patient = Patient(first_name="Alex", last_name="Stone", date_of_birth=datetime(1988, 6, 5).date())
    template = Template(
        name="Draft Ownership Template",
        description="Used for draft ownership tests.",
        is_active=True,
        created_by_user=admin,
    )
    encounter = Encounter(
        patient=patient,
        provider=provider_two,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
    )
    draft = EncounterDraft(encounter=encounter, transcript="Original", draft_revision=1)
    db_session.add_all([admin, provider_one, provider_two, patient, template, encounter, draft])
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "draft-provider-one@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.patch(
        f"/api/encounters/{encounter.id}/draft",
        json={"transcript": "Unauthorized update"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_provider_one_cannot_save_provider_two_note(client, db_session) -> None:
    admin = create_user("save-admin@example.com", UserRole.ADMIN)
    provider_one = create_user("save-provider-one@example.com", UserRole.PROVIDER)
    provider_two = create_user("save-provider-two@example.com", UserRole.PROVIDER)
    patient = Patient(first_name="Sam", last_name="Jordan", date_of_birth=datetime(1987, 8, 20).date())
    template = Template(
        name="Save Ownership Template",
        description="Used for note save ownership tests.",
        is_active=True,
        created_by_user=admin,
    )
    encounter = Encounter(
        patient=patient,
        provider=provider_two,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 15, 13, 0, tzinfo=UTC),
    )
    note = Note(encounter=encounter)
    db_session.add_all([admin, provider_one, provider_two, patient, template, encounter, note])
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "save-provider-one@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.post(
        f"/api/encounters/{encounter.id}/save",
        json={"subjective": "Unauthorized save attempt"},
    )
    assert response.status_code == 404
