from datetime import UTC, datetime

import pytest

from app.core.security import hash_password
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus, TemplateSectionType, UserRole
from app.db.models.provider_profile import ProviderProfile
from app.db.models.template import Template
from app.db.models.template_section import TemplateSection
from app.db.models.user import User
from app.db.models.patient import Patient


def create_user(email: str, role: UserRole, *, is_active: bool = True) -> User:
    return User(
        email=email,
        password_hash=hash_password("DemoPass123!"),
        role=role,
        is_active=is_active,
    )


def create_provider(email: str, *, is_active: bool = True) -> User:
    user = create_user(email, UserRole.PROVIDER, is_active=is_active)
    user.provider_profile = ProviderProfile(
        first_name="Maya",
        last_name="Chen",
        specialty="Family Medicine",
    )
    return user


@pytest.mark.asyncio
async def test_admin_dashboard_returns_counts_and_recent_encounters(client, db_session) -> None:
    admin = create_user("admin-dashboard@example.com", UserRole.ADMIN)
    provider = create_provider("provider-dashboard@example.com")
    patient = Patient(first_name="Jordan", last_name="Miles", date_of_birth=datetime(1990, 1, 1).date())
    template = Template(
        name="Admin Dashboard Template",
        description="Template for admin dashboard tests.",
        is_active=True,
        created_by_user=admin,
    )
    template.sections = [
        TemplateSection(section=TemplateSectionType.GENERAL, instructions="General", sort_order=0),
    ]
    encounter = Encounter(
        patient=patient,
        provider=provider,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 14, 10, 0, tzinfo=UTC),
    )
    db_session.add_all([admin, provider, patient, template, encounter])
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "admin-dashboard@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.get("/api/admin/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["active_provider_count"] == 1
    assert body["total_encounter_count"] == 1
    assert body["active_template_count"] == 1
    assert body["recent_encounters"][0]["patient_name"] == "Jordan Miles"


@pytest.mark.asyncio
async def test_admin_can_create_and_deactivate_provider(client, db_session) -> None:
    admin = create_user("admin-providers@example.com", UserRole.ADMIN)
    db_session.add(admin)
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "admin-providers@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    create_response = await client.post(
        "/api/admin/providers",
        json={
            "first_name": "Alicia",
            "last_name": "Wright",
            "email": "alicia.wright@example.com",
            "password": "DemoPass123!",
            "specialty": "Urgent Care",
        },
    )
    assert create_response.status_code == 201
    provider_id = create_response.json()["id"]

    status_response = await client.patch(
        f"/api/admin/providers/{provider_id}/status",
        json={"is_active": False},
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_encounter_list_supports_provider_filter_and_pagination(client, db_session) -> None:
    admin = create_user("admin-encounters@example.com", UserRole.ADMIN)
    provider_one = create_provider("provider-one-admin-list@example.com")
    provider_two = create_provider("provider-two-admin-list@example.com")
    patient_one = Patient(first_name="Jordan", last_name="Miles", date_of_birth=datetime(1990, 1, 1).date())
    patient_two = Patient(first_name="Alex", last_name="Stone", date_of_birth=datetime(1988, 6, 5).date())
    template = Template(
        name="Admin Encounter Template",
        description="Template for encounter list tests.",
        is_active=True,
        created_by_user=admin,
    )
    encounter_one = Encounter(
        patient=patient_one,
        provider=provider_one,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 14, 9, 0, tzinfo=UTC),
    )
    encounter_two = Encounter(
        patient=patient_two,
        provider=provider_two,
        template=template,
        status=EncounterStatus.COMPLETED,
        encounter_date=datetime(2026, 7, 15, 9, 0, tzinfo=UTC),
    )
    db_session.add_all([admin, provider_one, provider_two, patient_one, patient_two, template, encounter_one, encounter_two])
    await db_session.commit()

    login_response = await client.post(
        "/api/auth/login",
        json={"email": "admin-encounters@example.com", "password": "DemoPass123!"},
    )
    assert login_response.status_code == 200

    response = await client.get(
        "/api/encounters/admin/encounters",
        params={"provider_id": provider_two.id, "page": 1, "page_size": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["provider_id"] == provider_two.id


@pytest.mark.asyncio
async def test_admin_template_crud_updates_provider_visible_templates(client, db_session) -> None:
    admin = create_user("admin-templates@example.com", UserRole.ADMIN)
    provider = create_provider("provider-template-view@example.com")
    db_session.add_all([admin, provider])
    await db_session.commit()

    admin_login = await client.post(
        "/api/auth/login",
        json={"email": "admin-templates@example.com", "password": "DemoPass123!"},
    )
    assert admin_login.status_code == 200

    create_response = await client.post(
        "/api/admin/templates",
        json={
            "name": "Admin Managed Template",
            "description": "Initial description",
            "is_active": True,
            "sections": [
                {"section": "general", "instructions": "General guidance", "sort_order": 0},
                {"section": "subjective", "instructions": "Subjective guidance", "sort_order": 1},
                {"section": "objective", "instructions": "Objective guidance", "sort_order": 2},
                {"section": "assessment", "instructions": "Assessment guidance", "sort_order": 3},
                {"section": "plan", "instructions": "Plan guidance", "sort_order": 4},
            ],
        },
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["id"]

    update_response = await client.put(
        f"/api/admin/templates/{template_id}",
        json={
            "name": "Admin Managed Template",
            "description": "Updated description",
            "is_active": True,
            "sections": [
                {"section": "general", "instructions": "Updated general guidance", "sort_order": 0},
                {"section": "subjective", "instructions": "Updated subjective guidance", "sort_order": 1},
                {"section": "objective", "instructions": "Updated objective guidance", "sort_order": 2},
                {"section": "assessment", "instructions": "Updated assessment guidance", "sort_order": 3},
                {"section": "plan", "instructions": "Updated plan guidance", "sort_order": 4},
            ],
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Updated description"

    provider_login = await client.post(
        "/api/auth/login",
        json={"email": "provider-template-view@example.com", "password": "DemoPass123!"},
    )
    assert provider_login.status_code == 200

    provider_templates_response = await client.get("/api/templates")
    assert provider_templates_response.status_code == 200
    provider_templates = provider_templates_response.json()
    matched_template = next(template for template in provider_templates if template["id"] == template_id)
    assert matched_template["description"] == "Updated description"
    assert matched_template["sections"][0]["instructions"] == "Updated general guidance"
