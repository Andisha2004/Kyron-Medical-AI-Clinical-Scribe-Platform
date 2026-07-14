from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError

from app.core.security import hash_password
from app.db.models.audit_log import AuditLog
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus, UserRole
from app.db.models.icd10_code import Icd10Code
from app.db.models.note import Note
from app.db.models.note_version import NoteVersion
from app.db.models.patient import Patient
from app.db.models.template import Template
from app.db.models.user import User


def build_user(email: str, role: UserRole = UserRole.PROVIDER) -> User:
    return User(
        email=email,
        password_hash=hash_password("DemoPass123!"),
        role=role,
        is_active=True,
    )


async def create_encounter_fixture(db_session) -> tuple[User, User, Patient, Template, Encounter]:
    admin = build_user("phase2.admin@example.com", UserRole.ADMIN)
    provider = build_user("phase2.provider@example.com", UserRole.PROVIDER)
    patient = Patient(
        first_name="Jordan",
        last_name="Test",
        date_of_birth=date(1991, 4, 11),
    )
    template = Template(
        name="General Follow-Up Template",
        description="Template for persistence tests.",
        is_active=True,
        created_by_user=admin,
    )
    encounter = Encounter(
        patient=patient,
        provider=provider,
        template=template,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime(2026, 7, 13, 9, 30, tzinfo=UTC),
    )
    db_session.add_all([admin, provider, patient, template, encounter])
    await db_session.commit()
    return admin, provider, patient, template, encounter


@pytest.mark.asyncio
async def test_one_encounter_has_one_active_draft(db_session) -> None:
    _, _, _, _, encounter = await create_encounter_fixture(db_session)
    first_draft = EncounterDraft(
        encounter_id=encounter.id,
        transcript="Initial transcript",
        draft_revision=1,
    )
    second_draft = EncounterDraft(
        encounter_id=encounter.id,
        transcript="Duplicate draft",
        draft_revision=1,
    )

    db_session.add(first_draft)
    await db_session.commit()

    db_session.add(second_draft)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_draft_can_be_restored_after_refresh(db_session) -> None:
    _, _, _, _, encounter = await create_encounter_fixture(db_session)
    draft = EncounterDraft(
        encounter_id=encounter.id,
        transcript="Patient reports knee pain.",
        observations="Mild swelling noted.",
        subjective="Knee pain for two weeks.",
        objective=None,
        assessment="Likely overuse injury.",
        plan="Rest and follow-up.",
        selected_icd10_codes=[{"code": "M25.561", "description": "Pain in right knee"}],
        draft_revision=1,
    )
    db_session.add(draft)
    await db_session.commit()

    restored_draft = await db_session.scalar(
        select(EncounterDraft).where(EncounterDraft.encounter_id == encounter.id)
    )

    assert restored_draft is not None
    assert restored_draft.transcript == "Patient reports knee pain."
    assert restored_draft.selected_icd10_codes == [
        {"code": "M25.561", "description": "Pain in right knee"}
    ]


@pytest.mark.asyncio
async def test_draft_revision_increases_after_save(db_session) -> None:
    _, _, _, _, encounter = await create_encounter_fixture(db_session)
    draft = EncounterDraft(
        encounter_id=encounter.id,
        transcript="Initial transcript",
        draft_revision=1,
    )
    db_session.add(draft)
    await db_session.commit()
    await db_session.refresh(draft)

    original_updated_at = draft.updated_at
    draft.transcript = "Updated transcript"
    draft.subjective = "Updated subjective"
    await db_session.commit()
    await db_session.refresh(draft)

    assert draft.draft_revision == 2
    assert draft.updated_at > original_updated_at


@pytest.mark.asyncio
async def test_note_encounter_relation_is_unique(db_session) -> None:
    _, _, _, _, encounter = await create_encounter_fixture(db_session)
    first_note = Note(encounter_id=encounter.id)
    second_note = Note(encounter_id=encounter.id)

    db_session.add(first_note)
    await db_session.commit()

    db_session.add(second_note)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_note_can_reference_optional_current_version(db_session) -> None:
    admin, provider, _, _, encounter = await create_encounter_fixture(db_session)
    note = Note(encounter_id=encounter.id)
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)

    assert note.current_version_id is None

    version = NoteVersion(
        note_id=note.id,
        version_number=1,
        saved_by_user_id=provider.id,
        subjective="Patient reports improvement.",
        objective=None,
        assessment="Stable condition.",
        plan="Continue current treatment.",
        icd10_codes=[{"code": "Z09", "description": "Follow-up examination"}],
        generation_metadata={"source": "manual"},
    )
    db_session.add(version)
    await db_session.commit()
    await db_session.refresh(version)

    note.current_version_id = version.id
    await db_session.commit()
    await db_session.refresh(note)

    assert note.current_version_id == version.id


@pytest.mark.asyncio
async def test_saving_twice_creates_version_one_and_two_without_mutating_version_one(db_session) -> None:
    _, provider, _, _, encounter = await create_encounter_fixture(db_session)
    note = Note(encounter_id=encounter.id)
    db_session.add(note)
    await db_session.commit()

    version_one = NoteVersion(
        note_id=note.id,
        version_number=1,
        saved_by_user_id=provider.id,
        subjective="Initial subjective.",
        objective="Initial objective.",
        assessment="Initial assessment.",
        plan="Initial plan.",
        icd10_codes=[{"code": "M25.561", "description": "Pain in right knee"}],
        generation_metadata={"source": "ai"},
    )
    db_session.add(version_one)
    await db_session.commit()
    await db_session.refresh(version_one)

    version_two = NoteVersion(
        note_id=note.id,
        version_number=2,
        saved_by_user_id=provider.id,
        subjective="Updated subjective.",
        objective="Initial objective.",
        assessment="Updated assessment.",
        plan="Updated plan.",
        icd10_codes=[{"code": "M17.11", "description": "Right knee osteoarthritis"}],
        generation_metadata={"source": "manual"},
    )
    db_session.add(version_two)
    await db_session.commit()
    await db_session.refresh(version_two)
    await db_session.refresh(version_one)

    assert version_one.version_number == 1
    assert version_two.version_number == 2
    assert version_one.subjective == "Initial subjective."
    assert version_two.subjective == "Updated subjective."
    assert version_one.saved_at <= version_two.saved_at


@pytest.mark.asyncio
async def test_duplicate_note_version_number_is_rejected(db_session) -> None:
    _, provider, _, _, encounter = await create_encounter_fixture(db_session)
    note = Note(encounter_id=encounter.id)
    db_session.add(note)
    await db_session.commit()

    first_version = NoteVersion(
        note_id=note.id,
        version_number=1,
        saved_by_user_id=provider.id,
        subjective="Version one",
    )
    db_session.add(first_version)
    await db_session.commit()

    duplicate_version = NoteVersion(
        note_id=note.id,
        version_number=1,
        saved_by_user_id=provider.id,
        subjective="Duplicate version one",
    )
    db_session.add(duplicate_version)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_note_versions_are_immutable(db_session) -> None:
    _, provider, _, _, encounter = await create_encounter_fixture(db_session)
    note = Note(encounter_id=encounter.id)
    db_session.add(note)
    await db_session.commit()

    version = NoteVersion(
        note_id=note.id,
        version_number=1,
        saved_by_user_id=provider.id,
        subjective="Immutable content",
    )
    db_session.add(version)
    await db_session.commit()

    version.subjective = "Mutated content"
    with pytest.raises(ValueError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_icd10_code_must_be_unique_and_searchable(db_session) -> None:
    code = Icd10Code(
        code="M25.561",
        description="Pain in right knee",
        category="Musculoskeletal",
        search_text="pain right knee musculoskeletal arthralgia",
    )
    db_session.add(code)
    await db_session.commit()

    matched = await db_session.scalar(
        select(Icd10Code).where(Icd10Code.search_text.contains("right knee"))
    )
    assert matched is not None
    assert matched.code == "M25.561"

    duplicate = Icd10Code(
        code="M25.561",
        description="Duplicate pain code",
        category="Musculoskeletal",
        search_text="duplicate entry",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_audit_logs_allow_system_events_and_reject_full_note_metadata(db_session) -> None:
    system_event = AuditLog(
        actor_user_id=None,
        action="SYSTEM_IMPORT",
        entity_type="seed",
        entity_id=None,
        metadata_json={"record_count": 300, "source": "seed_demo"},
    )
    db_session.add(system_event)
    await db_session.commit()
    await db_session.refresh(system_event)

    assert system_event.actor_user_id is None

    with pytest.raises(ValueError):
        AuditLog(
            actor_user_id=None,
            action="NOTE_SAVED",
            entity_type="note_version",
            entity_id=None,
            metadata_json={
                "subjective": "Full note content should not be logged.",
                "source": "api",
            },
        )

