from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
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
from app.db.session import AsyncSessionLocal


DEMO_PASSWORD = "DemoPass123!"

DEMO_USERS = [
    {
        "email": "provider1@kyron-demo.com",
        "role": UserRole.PROVIDER,
        "first_name": "Maya",
        "last_name": "Chen",
        "specialty": "Family Medicine",
    },
    {
        "email": "provider2@kyron-demo.com",
        "role": UserRole.PROVIDER,
        "first_name": "Daniel",
        "last_name": "Brooks",
        "specialty": "Orthopedics",
    },
    {
        "email": "provider3@kyron-demo.com",
        "role": UserRole.PROVIDER,
        "first_name": "Alicia",
        "last_name": "Wright",
        "specialty": "Urgent Care",
    },
    {
        "email": "admin@kyron-demo.com",
        "role": UserRole.ADMIN,
        "first_name": "Nina",
        "last_name": "Patel",
        "specialty": None,
    },
]

TEMPLATES = [
    {
        "name": "Orthopedic Follow-Up",
        "description": "Focused on pain progression, mobility, prior therapy, and imaging.",
        "sections": [
            (TemplateSectionType.GENERAL, "Use concise orthopedic follow-up language.", 0),
            (TemplateSectionType.SUBJECTIVE, "Capture pain location, severity, duration, and triggers.", 1),
            (TemplateSectionType.OBJECTIVE, "Capture gait, swelling, range of motion, and tenderness when documented.", 2),
            (TemplateSectionType.ASSESSMENT, "Summarize likely musculoskeletal diagnosis and treatment response.", 3),
            (TemplateSectionType.PLAN, "Include therapy, imaging, medication, and follow-up guidance.", 4),
        ],
    },
    {
        "name": "New Patient Evaluation",
        "description": "General first-visit template for comprehensive evaluations.",
        "sections": [
            (TemplateSectionType.GENERAL, "Use professional language appropriate for a first evaluation.", 0),
            (TemplateSectionType.SUBJECTIVE, "Capture history of present illness, history, and patient concerns.", 1),
            (TemplateSectionType.OBJECTIVE, "Capture available examination findings and measurements only when provided.", 2),
            (TemplateSectionType.ASSESSMENT, "Summarize key problems and differential considerations.", 3),
            (TemplateSectionType.PLAN, "Include next diagnostic or therapeutic steps and follow-up.", 4),
        ],
    },
    {
        "name": "Urgent Care Visit",
        "description": "Prioritizes acute symptoms, red flags, and return precautions.",
        "sections": [
            (TemplateSectionType.GENERAL, "Prioritize acute symptom clarity and safety guidance.", 0),
            (TemplateSectionType.SUBJECTIVE, "Capture onset, severity, associated symptoms, and negatives.", 1),
            (TemplateSectionType.OBJECTIVE, "Capture vitals and focused exam only when explicitly available.", 2),
            (TemplateSectionType.ASSESSMENT, "Summarize acute working diagnosis and major rule-outs.", 3),
            (TemplateSectionType.PLAN, "Include treatment, testing, and return precautions.", 4),
        ],
    },
]


def icd_seed_entries() -> list[dict[str, str | None]]:
    curated_entries = [
        ("M17.11", "Unilateral primary osteoarthritis, right knee", "Musculoskeletal", ["right knee arthritis", "knee osteoarthritis"]),
        ("M25.561", "Pain in right knee", "Musculoskeletal", ["right knee pain", "knee pain"]),
        ("M54.50", "Low back pain, unspecified", "Musculoskeletal", ["back pain", "lumbar pain"]),
        ("J06.9", "Acute upper respiratory infection, unspecified", "Respiratory", ["uri", "cold symptoms"]),
        ("R05.9", "Cough, unspecified", "Respiratory", ["cough"]),
        ("J02.9", "Acute pharyngitis, unspecified", "Respiratory", ["sore throat"]),
        ("I10", "Essential (primary) hypertension", "Cardiovascular", ["hypertension", "high blood pressure"]),
        ("E11.9", "Type 2 diabetes mellitus without complications", "Endocrine", ["type 2 diabetes", "diabetes follow-up"]),
        ("K21.9", "Gastro-esophageal reflux disease without esophagitis", "Gastrointestinal", ["gerd", "acid reflux"]),
        ("F41.9", "Anxiety disorder, unspecified", "Mental Health", ["anxiety"]),
        ("L30.9", "Dermatitis, unspecified", "Dermatology", ["rash", "dermatitis"]),
        ("N39.0", "Urinary tract infection, site not specified", "Genitourinary", ["uti", "urinary infection"]),
    ]

    entries: list[dict[str, str | None]] = []
    for code, description, category, aliases in curated_entries:
        search_text = " ".join([code.lower(), description.lower(), *(alias.lower() for alias in aliases)])
        entries.append(
            {
                "code": code,
                "description": description,
                "category": category,
                "search_text": search_text,
            }
        )

    categories = {
        "Musculoskeletal": ["knee pain", "back pain", "shoulder strain", "ankle sprain", "joint stiffness"],
        "Respiratory": ["cough", "congestion", "sore throat", "viral symptoms", "shortness of breath"],
        "Cardiovascular": ["hypertension", "palpitations", "chest discomfort", "follow-up monitoring", "edema"],
        "Endocrine": ["diabetes follow-up", "thyroid disorder", "glucose monitoring", "metabolic concern", "fatigue"],
        "Gastrointestinal": ["abdominal pain", "nausea", "reflux", "constipation", "diarrhea"],
        "Mental Health": ["anxiety symptoms", "depressed mood", "sleep disturbance", "stress reaction", "panic symptoms"],
        "Dermatology": ["rash", "eczema flare", "itching", "skin irritation", "dermatitis"],
        "Genitourinary": ["urinary symptoms", "pelvic discomfort", "frequency", "burning urination", "uti follow-up"],
    }

    prefixes = {
        "Musculoskeletal": "M",
        "Respiratory": "J",
        "Cardiovascular": "I",
        "Endocrine": "E",
        "Gastrointestinal": "K",
        "Mental Health": "F",
        "Dermatology": "L",
        "Genitourinary": "N",
    }

    counter = 0
    for category, phrases in categories.items():
        prefix = prefixes[category]
        for group_number in range(1, 9):
            for phrase_index, phrase in enumerate(phrases, start=1):
                counter += 1
                code = f"{prefix}{group_number:02d}.{phrase_index:01d}{counter % 10}"
                description = f"{category} demo code {counter:03d} for {phrase}"
                search_text = f"{code.lower()} {description.lower()} {phrase.lower()} {category.lower()}"
                entries.append(
                    {
                        "code": code,
                        "description": description,
                        "category": category,
                        "search_text": search_text,
                    }
                )
                if len(entries) >= 320:
                    return entries

    return entries


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(select(User).where(User.email == email.lower()))


async def get_template_by_name(session: AsyncSession, name: str) -> Template | None:
    return await session.scalar(select(Template).where(Template.name == name))


async def get_patient(session: AsyncSession, first_name: str, last_name: str, dob: date) -> Patient | None:
    return await session.scalar(
        select(Patient).where(
            Patient.normalized_first_name == first_name.strip().lower(),
            Patient.normalized_last_name == last_name.strip().lower(),
            Patient.date_of_birth == dob,
        )
    )


async def ensure_user(session: AsyncSession, user_data: dict[str, object]) -> User:
    email = str(user_data["email"]).lower()
    existing_user = await get_user_by_email(session, email)
    if existing_user:
        existing_user.role = user_data["role"]  # type: ignore[assignment]
        existing_user.is_active = True
        if not verify_password(DEMO_PASSWORD, existing_user.password_hash):
            existing_user.password_hash = hash_password(DEMO_PASSWORD)
        await session.flush()
        user = existing_user
    else:
        user = User(
            email=email,
            password_hash=hash_password(DEMO_PASSWORD),
            role=user_data["role"],  # type: ignore[arg-type]
            is_active=True,
        )
        session.add(user)
        await session.flush()

    if user.role == UserRole.PROVIDER:
        profile = await session.scalar(
            select(ProviderProfile).where(ProviderProfile.user_id == user.id)
        )
        if profile is None:
            session.add(
                ProviderProfile(
                    user_id=user.id,
                    first_name=str(user_data["first_name"]),
                    last_name=str(user_data["last_name"]),
                    specialty=user_data["specialty"],  # type: ignore[arg-type]
                )
            )
        else:
            profile.first_name = str(user_data["first_name"])
            profile.last_name = str(user_data["last_name"])
            profile.specialty = user_data["specialty"]  # type: ignore[assignment]

    await session.flush()
    return user


async def ensure_template(session: AsyncSession, admin_user: User, template_data: dict[str, object]) -> Template:
    template = await get_template_by_name(session, str(template_data["name"]))
    if template is None:
        template = Template(
            name=str(template_data["name"]),
            description=template_data["description"],  # type: ignore[arg-type]
            is_active=True,
            created_by_user_id=admin_user.id,
        )
        session.add(template)
        await session.flush()
    else:
        template.description = template_data["description"]  # type: ignore[assignment]
        template.is_active = True
        template.deleted_at = None

    existing_sections = {
        section.section: section
        for section in (
            await session.scalars(
                select(TemplateSection).where(TemplateSection.template_id == template.id)
            )
        ).all()
    }
    for section_type, instructions, sort_order in template_data["sections"]:  # type: ignore[index]
        current_section = existing_sections.get(section_type)
        if current_section:
            current_section.instructions = instructions
            current_section.sort_order = sort_order
        else:
            session.add(
                TemplateSection(
                    template_id=template.id,
                    section=section_type,
                    instructions=instructions,
                    sort_order=sort_order,
                )
            )

    await session.flush()
    return template


async def ensure_patient(session: AsyncSession, first_name: str, last_name: str, dob: date) -> Patient:
    patient = await get_patient(session, first_name, last_name, dob)
    if patient:
        return patient

    patient = Patient(first_name=first_name, last_name=last_name, date_of_birth=dob)
    session.add(patient)
    await session.flush()
    return patient


async def ensure_completed_encounter_with_note(
    session: AsyncSession,
    patient: Patient,
    provider: User,
    template: Template,
    encounter_date: datetime,
    version_payloads: Iterable[dict[str, object]],
) -> Encounter:
    existing_encounter = await session.scalar(
        select(Encounter).where(
            Encounter.patient_id == patient.id,
            Encounter.provider_id == provider.id,
            Encounter.template_id == template.id,
            Encounter.encounter_date == encounter_date,
        )
    )
    if existing_encounter is None:
        encounter = Encounter(
            patient_id=patient.id,
            provider_id=provider.id,
            template_id=template.id,
            status=EncounterStatus.COMPLETED,
            encounter_date=encounter_date,
        )
        session.add(encounter)
        await session.flush()
    else:
        encounter = existing_encounter
        encounter.status = EncounterStatus.COMPLETED

    note = await session.scalar(select(Note).where(Note.encounter_id == encounter.id))
    if note is None:
        note = Note(encounter_id=encounter.id)
        session.add(note)
        await session.flush()

    existing_versions = {
        version.version_number: version
        for version in (
            await session.scalars(select(NoteVersion).where(NoteVersion.note_id == note.id))
        ).all()
    }
    latest_version: NoteVersion | None = None
    for payload in version_payloads:
        version_number = int(payload["version_number"])
        version = existing_versions.get(version_number)
        if version is None:
            version = NoteVersion(
                note_id=note.id,
                version_number=version_number,
                saved_by_user_id=provider.id,
                subjective=payload.get("subjective"),  # type: ignore[arg-type]
                objective=payload.get("objective"),  # type: ignore[arg-type]
                assessment=payload.get("assessment"),  # type: ignore[arg-type]
                plan=payload.get("plan"),  # type: ignore[arg-type]
                icd10_codes=payload.get("icd10_codes"),  # type: ignore[arg-type]
                generation_metadata=payload.get("generation_metadata"),  # type: ignore[arg-type]
            )
            session.add(version)
            await session.flush()
        latest_version = version

    if latest_version is not None and note.current_version_id != latest_version.id:
        note.current_version_id = latest_version.id
        await session.flush()

    return encounter


async def ensure_draft_encounter(
    session: AsyncSession,
    patient: Patient,
    provider: User,
    template: Template,
    encounter_date: datetime,
    transcript: str,
    subjective: str,
    assessment: str,
    plan: str,
    icd_codes: list[dict[str, str]],
) -> Encounter:
    encounter = await session.scalar(
        select(Encounter).where(
            Encounter.patient_id == patient.id,
            Encounter.provider_id == provider.id,
            Encounter.template_id == template.id,
            Encounter.encounter_date == encounter_date,
        )
    )
    if encounter is None:
        encounter = Encounter(
            patient_id=patient.id,
            provider_id=provider.id,
            template_id=template.id,
            status=EncounterStatus.DRAFT,
            encounter_date=encounter_date,
        )
        session.add(encounter)
        await session.flush()
    else:
        encounter.status = EncounterStatus.DRAFT

    draft = await session.scalar(
        select(EncounterDraft).where(EncounterDraft.encounter_id == encounter.id)
    )
    if draft is None:
        session.add(
            EncounterDraft(
                encounter_id=encounter.id,
                transcript=transcript,
                observations=None,
                subjective=subjective,
                objective=None,
                assessment=assessment,
                plan=plan,
                selected_icd10_codes=icd_codes,
                draft_revision=1,
            )
        )
    else:
        draft.transcript = transcript
        draft.subjective = subjective
        draft.assessment = assessment
        draft.plan = plan
        draft.selected_icd10_codes = icd_codes

    await session.flush()
    return encounter


async def ensure_icd_codes(session: AsyncSession) -> int:
    entries = icd_seed_entries()
    added_or_updated = 0
    for entry in entries:
        code = str(entry["code"])
        existing = await session.scalar(select(Icd10Code).where(Icd10Code.code == code))
        if existing is None:
            session.add(
                Icd10Code(
                    code=code,
                    description=str(entry["description"]),
                    category=entry["category"],  # type: ignore[arg-type]
                    search_text=str(entry["search_text"]),
                )
            )
        else:
            existing.description = str(entry["description"])
            existing.category = entry["category"]  # type: ignore[assignment]
            existing.search_text = str(entry["search_text"])
        added_or_updated += 1

    await session.flush()
    return added_or_updated


async def seed() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        users: dict[str, User] = {}
        for user_data in DEMO_USERS:
            user = await ensure_user(session, user_data)
            users[user.email] = user

        admin_user = users["admin@kyron-demo.com"]

        templates: dict[str, Template] = {}
        for template_data in TEMPLATES:
            template = await ensure_template(session, admin_user, template_data)
            templates[template.name] = template

        returning_patient = await ensure_patient(session, "Maria", "Lopez", date(1964, 3, 14))
        first_time_patient = await ensure_patient(session, "Jordan", "Test", date(1990, 1, 1))
        urgent_patient = await ensure_patient(session, "Taylor", "Nguyen", date(1988, 9, 22))
        follow_up_patient = await ensure_patient(session, "Avery", "Stone", date(1975, 6, 8))

        await ensure_completed_encounter_with_note(
            session,
            patient=returning_patient,
            provider=users["provider2@kyron-demo.com"],
            template=templates["Orthopedic Follow-Up"],
            encounter_date=datetime(2026, 6, 10, 10, 0, tzinfo=UTC),
            version_payloads=[
                {
                    "version_number": 1,
                    "subjective": "Patient reports chronic right knee pain for six months with stair-related worsening.",
                    "objective": "No objective findings were documented during the prior encounter.",
                    "assessment": "Likely right knee osteoarthritis.",
                    "plan": "Begin physical therapy and topical diclofenac. Follow up in four weeks.",
                    "icd10_codes": [{"code": "M17.11", "description": "Unilateral primary osteoarthritis, right knee"}],
                    "generation_metadata": {"source": "seed_demo", "encounter_type": "history"},
                },
                {
                    "version_number": 2,
                    "subjective": "Patient reports chronic right knee pain with partial improvement after physical therapy.",
                    "objective": "No objective findings were documented during the prior encounter.",
                    "assessment": "Right knee osteoarthritis with partial response to conservative therapy.",
                    "plan": "Continue physical therapy, continue topical diclofenac, and monitor symptoms on stairs.",
                    "icd10_codes": [{"code": "M17.11", "description": "Unilateral primary osteoarthritis, right knee"}],
                    "generation_metadata": {"source": "seed_demo", "encounter_type": "history_revision"},
                },
            ],
        )

        await ensure_draft_encounter(
            session,
            patient=returning_patient,
            provider=users["provider2@kyron-demo.com"],
            template=templates["Orthopedic Follow-Up"],
            encounter_date=datetime(2026, 7, 13, 9, 0, tzinfo=UTC),
            transcript="The patient returns for right knee pain. She says physical therapy helped slightly but pain persists on stairs.",
            subjective="Patient returns for follow-up of right knee pain with partial improvement after physical therapy.",
            assessment="Persistent right knee osteoarthritis symptoms.",
            plan="Consider repeat evaluation, continue exercises, and review pain management options.",
            icd_codes=[{"code": "M17.11", "description": "Unilateral primary osteoarthritis, right knee"}],
        )

        await ensure_draft_encounter(
            session,
            patient=first_time_patient,
            provider=users["provider1@kyron-demo.com"],
            template=templates["New Patient Evaluation"],
            encounter_date=datetime(2026, 7, 13, 11, 0, tzinfo=UTC),
            transcript="Patient reports intermittent headaches for three days with no fever and no visual changes.",
            subjective="Intermittent headaches for three days. Denies fever and visual changes.",
            assessment="Headache requiring further evaluation.",
            plan="Review hydration, rest, and monitor progression.",
            icd_codes=[{"code": "R51.9", "description": "Headache, unspecified"}],
        )

        await ensure_completed_encounter_with_note(
            session,
            patient=urgent_patient,
            provider=users["provider3@kyron-demo.com"],
            template=templates["Urgent Care Visit"],
            encounter_date=datetime(2026, 7, 12, 15, 30, tzinfo=UTC),
            version_payloads=[
                {
                    "version_number": 1,
                    "subjective": "Patient reports cough and sore throat for three days with temperature up to 100.4 at home.",
                    "objective": "No chest pain or shortness of breath documented. Hydration reported as adequate.",
                    "assessment": "Acute upper respiratory infection.",
                    "plan": "Supportive care, hydration, and return precautions for worsening symptoms.",
                    "icd10_codes": [{"code": "J06.9", "description": "Acute upper respiratory infection, unspecified"}],
                    "generation_metadata": {"source": "seed_demo", "encounter_type": "urgent_care"},
                }
            ],
        )

        await ensure_completed_encounter_with_note(
            session,
            patient=follow_up_patient,
            provider=users["provider1@kyron-demo.com"],
            template=templates["New Patient Evaluation"],
            encounter_date=datetime(2026, 7, 10, 13, 15, tzinfo=UTC),
            version_payloads=[
                {
                    "version_number": 1,
                    "subjective": "Patient reports elevated home blood pressure readings over the past two weeks.",
                    "objective": "No objective findings documented in the seed note.",
                    "assessment": "Hypertension follow-up.",
                    "plan": "Review home readings, lifestyle modifications, and medication adherence.",
                    "icd10_codes": [{"code": "I10", "description": "Essential (primary) hypertension"}],
                    "generation_metadata": {"source": "seed_demo", "encounter_type": "completed"},
                }
            ],
        )

        icd_count = await ensure_icd_codes(session)

        session.add(
            AuditLog(
                actor_user_id=None,
                action="SEED_DEMO_COMPLETED",
                entity_type="seed",
                entity_id=None,
                metadata_json={
                    "users_seeded": len(DEMO_USERS),
                    "templates_seeded": len(TEMPLATES),
                    "icd_codes_seeded": icd_count,
                },
            )
        )

        await session.commit()

        if settings.app_env != "production":
            print("Demo credentials")
            for user_data in DEMO_USERS:
                print(f"- {user_data['email']} / {DEMO_PASSWORD}")
        print("Seed complete.")
        print(f"Users ensured: {len(DEMO_USERS)}")
        print(f"Templates ensured: {len(TEMPLATES)}")
        print(f"ICD-10 entries ensured: {icd_count}")


if __name__ == "__main__":
    asyncio.run(seed())
