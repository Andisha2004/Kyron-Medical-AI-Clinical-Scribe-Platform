from datetime import date, datetime, UTC

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError

from app.core.security import hash_password
from app.db.models.encounter import Encounter
from app.db.models.enums import EncounterStatus, TemplateSectionType, UserRole
from app.db.models.patient import Patient
from app.db.models.template import Template
from app.db.models.template_section import TemplateSection
from app.db.models.user import User


def build_user(email: str, role: UserRole = UserRole.PROVIDER) -> User:
    return User(
        email=email,
        password_hash=hash_password("DemoPass123!"),
        role=role,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_patient_names_are_normalized_for_case_insensitive_matching(db_session) -> None:
    patient = Patient(
        first_name="  Maria  ",
        last_name="  LOPEZ ",
        date_of_birth=date(1985, 7, 14),
    )
    db_session.add(patient)
    await db_session.commit()
    await db_session.refresh(patient)

    assert patient.first_name == "Maria"
    assert patient.last_name == "LOPEZ"
    assert patient.normalized_first_name == "maria"
    assert patient.normalized_last_name == "lopez"

    matched_patient = await db_session.scalar(
        select(Patient).where(
            Patient.normalized_last_name == "lopez",
            Patient.normalized_first_name == "maria",
            Patient.date_of_birth == date(1985, 7, 14),
        )
    )

    assert matched_patient is not None
    assert matched_patient.id == patient.id


@pytest.mark.asyncio
async def test_patient_requires_date_of_birth(db_session) -> None:
    patient = Patient(
        first_name="Jordan",
        last_name="Test",
        date_of_birth=None,  # type: ignore[arg-type]
    )
    db_session.add(patient)

    with pytest.raises((IntegrityError, StatementError)):
        await db_session.commit()


@pytest.mark.asyncio
async def test_patient_can_have_multiple_encounters(db_session) -> None:
    creator = build_user("creator.patient.encounters@example.com", UserRole.ADMIN)
    provider = build_user("provider.patient.encounters@example.com")
    patient = Patient(
        first_name="Avery",
        last_name="Stone",
        date_of_birth=date(1992, 3, 9),
    )
    template = Template(
        name="Orthopedic Follow-Up",
        description="Template for follow-up visits.",
        is_active=True,
        created_by_user=creator,
    )

    db_session.add_all([creator, provider, patient, template])
    await db_session.commit()

    first_encounter = Encounter(
        patient=patient,
        provider=provider,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 13, 10, 0, tzinfo=UTC),
    )
    second_encounter = Encounter(
        patient=patient,
        provider=provider,
        template=template,
        status=EncounterStatus.COMPLETED,
        encounter_date=datetime(2026, 7, 14, 11, 0, tzinfo=UTC),
    )
    db_session.add_all([first_encounter, second_encounter])
    await db_session.commit()
    await db_session.refresh(patient, ["encounters"])

    assert len(patient.encounters) == 2


@pytest.mark.asyncio
async def test_template_name_must_be_unique(db_session) -> None:
    creator = build_user("template.creator.unique@example.com", UserRole.ADMIN)
    first_template = Template(
        name="Urgent Care Visit",
        description="Initial template.",
        is_active=True,
        created_by_user=creator,
    )

    db_session.add_all([creator, first_template])
    await db_session.commit()

    duplicate_template = Template(
        name="Urgent Care Visit",
        description="Duplicate template.",
        is_active=False,
        created_by_user_id=creator.id,
    )
    db_session.add(duplicate_template)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_template_tracks_creator_and_active_status(db_session) -> None:
    creator = build_user("template.creator.status@example.com", UserRole.ADMIN)
    inactive_template = Template(
        name="Inactive Follow-Up Template",
        description="Kept for historical encounters only.",
        is_active=False,
        created_by_user=creator,
    )

    db_session.add_all([creator, inactive_template])
    await db_session.commit()
    await db_session.refresh(inactive_template, ["created_by_user"])

    assert inactive_template.is_active is False
    assert inactive_template.created_by_user.id == creator.id


@pytest.mark.asyncio
async def test_template_supports_all_section_types(db_session) -> None:
    creator = build_user("template.creator.sections@example.com", UserRole.ADMIN)
    template = Template(
        name="Complete SOAP Template",
        description="Supports general and SOAP instructions.",
        is_active=True,
        created_by_user=creator,
    )
    sections = [
        TemplateSection(
            template=template,
            section=TemplateSectionType.GENERAL,
            instructions="General documentation rules.",
            sort_order=0,
        ),
        TemplateSection(
            template=template,
            section=TemplateSectionType.SUBJECTIVE,
            instructions="Capture reported symptoms.",
            sort_order=1,
        ),
        TemplateSection(
            template=template,
            section=TemplateSectionType.OBJECTIVE,
            instructions="Capture observed findings.",
            sort_order=2,
        ),
        TemplateSection(
            template=template,
            section=TemplateSectionType.ASSESSMENT,
            instructions="Summarize diagnoses.",
            sort_order=3,
        ),
        TemplateSection(
            template=template,
            section=TemplateSectionType.PLAN,
            instructions="Document next steps.",
            sort_order=4,
        ),
    ]

    db_session.add_all([creator, template, *sections])
    await db_session.commit()
    await db_session.refresh(template, ["sections"])

    assert {section.section for section in template.sections} == {
        TemplateSectionType.GENERAL,
        TemplateSectionType.SUBJECTIVE,
        TemplateSectionType.OBJECTIVE,
        TemplateSectionType.ASSESSMENT,
        TemplateSectionType.PLAN,
    }


@pytest.mark.asyncio
async def test_duplicate_template_sections_are_rejected(db_session) -> None:
    creator = build_user("template.creator.duplicate-section@example.com", UserRole.ADMIN)
    template = Template(
        name="Duplicate Section Template",
        description="Should reject duplicate section names.",
        is_active=True,
        created_by_user=creator,
    )
    first_section = TemplateSection(
        template=template,
        section=TemplateSectionType.SUBJECTIVE,
        instructions="First subjective instructions.",
        sort_order=1,
    )

    db_session.add_all([creator, template, first_section])
    await db_session.commit()

    duplicate_section = TemplateSection(
        template_id=template.id,
        section=TemplateSectionType.SUBJECTIVE,
        instructions="Duplicate subjective instructions.",
        sort_order=2,
    )
    db_session.add(duplicate_section)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_encounter_belongs_to_one_provider_one_patient_and_one_template(db_session) -> None:
    creator = build_user("template.creator.encounter@example.com", UserRole.ADMIN)
    provider = build_user("provider.encounter@example.com")
    patient = Patient(
        first_name="Taylor",
        last_name="Brooks",
        date_of_birth=date(1979, 12, 1),
    )
    template = Template(
        name="Encounter Ownership Template",
        description="Verifies encounter relationships.",
        is_active=True,
        created_by_user=creator,
    )
    encounter = Encounter(
        patient=patient,
        provider=provider,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 13, 14, 30, tzinfo=UTC),
    )

    db_session.add_all([creator, provider, patient, template, encounter])
    await db_session.commit()
    await db_session.refresh(encounter, ["patient", "provider", "template"])

    assert encounter.patient.id == patient.id
    assert encounter.provider.id == provider.id
    assert encounter.template.id == template.id


@pytest.mark.asyncio
async def test_provider_can_have_multiple_encounters(db_session) -> None:
    creator = build_user("template.creator.provider-multi@example.com", UserRole.ADMIN)
    provider = build_user("provider.multi.encounters@example.com")
    first_patient = Patient(
        first_name="Morgan",
        last_name="Hill",
        date_of_birth=date(1988, 5, 2),
    )
    second_patient = Patient(
        first_name="Jamie",
        last_name="Reed",
        date_of_birth=date(1990, 9, 18),
    )
    template = Template(
        name="Multi Encounter Template",
        description="Shared template.",
        is_active=True,
        created_by_user=creator,
    )
    first_encounter = Encounter(
        patient=first_patient,
        provider=provider,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 15, 9, 0, tzinfo=UTC),
    )
    second_encounter = Encounter(
        patient=second_patient,
        provider=provider,
        template=template,
        status=EncounterStatus.COMPLETED,
        encounter_date=datetime(2026, 7, 16, 15, 45, tzinfo=UTC),
    )

    db_session.add_all(
        [
            creator,
            provider,
            first_patient,
            second_patient,
            template,
            first_encounter,
            second_encounter,
        ]
    )
    await db_session.commit()
    await db_session.refresh(provider, ["created_encounters"])

    assert len(provider.created_encounters) == 2
