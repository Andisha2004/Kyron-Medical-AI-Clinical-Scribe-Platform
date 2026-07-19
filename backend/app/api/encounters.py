import asyncio
import logging
import json
from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import (
    get_accessible_encounter,
    get_database_session,
    get_provider_owned_encounter,
    require_admin,
    require_provider,
)
from app.clients.openai_client import AiClientError
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.enums import EncounterStatus
from app.db.models.note import Note
from app.db.models.note_version import NoteVersion
from app.db.models.patient import Patient
from app.db.models.provider_profile import ProviderProfile
from app.db.models.template import Template
from app.db.models.user import User
from app.schemas.encounter import (
    CreateEncounterRequest,
    CreateEncounterResponse,
    EncounterDetailResponse,
    EncounterDraftResponse,
    EncounterDraftUpdateRequest,
    EncounterPatientResponse,
    EncounterResponse,
    EncounterTemplateResponse,
    EncounterVersionSummaryResponse,
    ProviderDashboardEncounterResponse,
    ProviderDashboardResponse,
    SaveEncounterNoteRequest,
    SaveEncounterNoteResponse,
)
from app.schemas.admin import AdminEncounterListItemResponse, AdminEncounterListResponse
from app.services.audit_service import AuditService
from app.services.note_generation_service import (
    InsufficientClinicalContentError,
    NoteGenerationService,
    get_note_generation_service,
)

router = APIRouter(prefix="/encounters", tags=["encounters"])
logger = logging.getLogger(__name__)


def serialize_draft(draft: EncounterDraft | None, encounter_id: str) -> EncounterDraftResponse | None:
    if draft is None:
        return None

    return EncounterDraftResponse(
        encounter_id=encounter_id,
        transcript=draft.transcript,
        observations=draft.observations,
        subjective=draft.subjective,
        objective=draft.objective,
        assessment=draft.assessment,
        plan=draft.plan,
        selected_icd10_codes=draft.selected_icd10_codes,
        draft_revision=draft.draft_revision,
        updated_at=draft.updated_at,
    )


def format_sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def chunk_text(value: str, chunk_size: int = 180) -> list[str]:
    text = value.strip()
    if not text:
        return []

    chunks: list[str] = []
    remaining = text
    while len(remaining) > chunk_size:
        split_index = remaining.rfind(" ", 0, chunk_size)
        if split_index == -1:
            split_index = chunk_size
        chunks.append(remaining[:split_index].strip() + " ")
        remaining = remaining[split_index:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


@router.get("/status")
async def encounters_status(_: User = Depends(require_provider)) -> dict[str, str]:
    return {"status": "authenticated"}


@router.get("/admin/encounters", response_model=AdminEncounterListResponse)
async def list_admin_encounters(
    provider_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 10,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_database_session),
) -> AdminEncounterListResponse:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 50)

    filters = []
    if provider_id:
        filters.append(Encounter.provider_id == provider_id)
    if start_date:
        filters.append(Encounter.encounter_date >= datetime.combine(start_date, time.min, tzinfo=UTC))
    if end_date:
        filters.append(Encounter.encounter_date <= datetime.combine(end_date, time.max, tzinfo=UTC))

    total = await session.scalar(select(func.count(Encounter.id)).where(*filters))
    encounters = (
        await session.scalars(
            select(Encounter)
            .where(*filters)
            .options(
                selectinload(Encounter.patient),
                selectinload(Encounter.provider).selectinload(User.provider_profile),
                selectinload(Encounter.template),
            )
            .order_by(Encounter.updated_at.desc(), Encounter.encounter_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).unique().all()

    return AdminEncounterListResponse(
        items=[
            AdminEncounterListItemResponse(
                id=encounter.id,
                provider_id=encounter.provider_id,
                provider_name=(
                    f"{encounter.provider.provider_profile.first_name} {encounter.provider.provider_profile.last_name}"
                    if encounter.provider.provider_profile
                    else encounter.provider.email
                ),
                patient_name=f"{encounter.patient.first_name} {encounter.patient.last_name}",
                encounter_date=encounter.encounter_date,
                status=encounter.status.value,
                template_name=encounter.template.name,
                updated_at=encounter.updated_at,
            )
            for encounter in encounters
        ],
        page=page,
        page_size=page_size,
        total=total or 0,
    )


@router.get("", response_model=ProviderDashboardResponse)
async def list_provider_encounters(
    current_user: User = Depends(require_provider),
    session: AsyncSession = Depends(get_database_session),
) -> ProviderDashboardResponse:
    provider_profile = await session.scalar(
        select(ProviderProfile).where(ProviderProfile.user_id == current_user.id)
    )
    result = await session.scalars(
        select(Encounter)
        .where(Encounter.provider_id == current_user.id)
        .options(selectinload(Encounter.patient), selectinload(Encounter.template))
        .order_by(Encounter.updated_at.desc(), Encounter.encounter_date.desc())
    )
    encounters = result.unique().all()

    provider_name = current_user.email
    if provider_profile is not None:
        provider_name = f"{provider_profile.first_name} {provider_profile.last_name}"

    return ProviderDashboardResponse(
        provider_name=provider_name,
        draft_count=sum(1 for encounter in encounters if encounter.status == EncounterStatus.DRAFT),
        completed_count=sum(
            1 for encounter in encounters if encounter.status == EncounterStatus.COMPLETED
        ),
        encounters=[
            ProviderDashboardEncounterResponse(
                id=encounter.id,
                patient_name=f"{encounter.patient.first_name} {encounter.patient.last_name}",
                encounter_date=encounter.encounter_date,
                last_updated_at=encounter.updated_at,
                status=encounter.status,
                template_name=encounter.template.name,
            )
            for encounter in encounters
        ],
    )


@router.post("", response_model=CreateEncounterResponse, status_code=status.HTTP_201_CREATED)
async def create_encounter(
    payload: CreateEncounterRequest,
    current_user: User = Depends(require_provider),
    session: AsyncSession = Depends(get_database_session),
) -> CreateEncounterResponse:
    template = await session.get(Template, payload.template_id)
    if template is None or not template.is_active or template.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active template not found.")

    normalized_first_name = Patient.normalize_name(payload.first_name)
    normalized_last_name = Patient.normalize_name(payload.last_name)

    patient = await session.scalar(
        select(Patient).where(
            Patient.normalized_first_name == normalized_first_name,
            Patient.normalized_last_name == normalized_last_name,
            Patient.date_of_birth == payload.date_of_birth,
        )
    )
    reused_existing_patient = patient is not None

    if patient is None:
        patient = Patient(
            first_name=payload.first_name,
            last_name=payload.last_name,
            date_of_birth=payload.date_of_birth,
        )
        session.add(patient)
        await session.flush()

    prior_encounter_count = await session.scalar(
        select(func.count(Encounter.id)).where(Encounter.patient_id == patient.id)
    )
    encounter = Encounter(
        patient_id=patient.id,
        provider_id=current_user.id,
        template_id=template.id,
        status=EncounterStatus.DRAFT,
        encounter_date=datetime.now(UTC),
    )
    session.add(encounter)
    await session.flush()

    draft = EncounterDraft(encounter_id=encounter.id, draft_revision=1)
    session.add(draft)

    await AuditService.log_event(
        session,
        action="ENCOUNTER_CREATED",
        entity_type="encounter",
        entity_id=encounter.id,
        actor_user_id=current_user.id,
        metadata_json={
            "patient_id": patient.id,
            "template_id": template.id,
            "reused_existing_patient": reused_existing_patient,
        },
    )
    await session.commit()
    await session.refresh(draft)

    return CreateEncounterResponse(
        encounter_id=encounter.id,
        patient_id=patient.id,
        draft_id=draft.id,
        reused_existing_patient=reused_existing_patient,
        has_prior_history=(prior_encounter_count or 0) > 0,
        prior_encounter_count=prior_encounter_count or 0,
    )


@router.get("/{encounter_id}", response_model=EncounterDetailResponse)
async def get_encounter(encounter: Encounter = Depends(get_accessible_encounter), session: AsyncSession = Depends(get_database_session)) -> EncounterDetailResponse:
    result = await session.scalar(
        select(Encounter)
        .where(Encounter.id == encounter.id)
        .options(
            selectinload(Encounter.patient),
            selectinload(Encounter.template),
            selectinload(Encounter.draft),
            selectinload(Encounter.note).selectinload(Note.versions),
        )
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found.")

    note = result.note
    versions = sorted(note.versions, key=lambda item: item.version_number, reverse=True) if note else []

    return EncounterDetailResponse(
        id=result.id,
        patient_id=result.patient_id,
        provider_id=result.provider_id,
        template_id=result.template_id,
        status=result.status,
        encounter_date=result.encounter_date,
        patient=EncounterPatientResponse(
            id=result.patient.id,
            first_name=result.patient.first_name,
            last_name=result.patient.last_name,
            date_of_birth=result.patient.date_of_birth,
        ),
        template=EncounterTemplateResponse(
            id=result.template.id,
            name=result.template.name,
            description=result.template.description,
            is_active=result.template.is_active,
        ),
        draft=serialize_draft(result.draft, result.id),
        note_id=note.id if note else None,
        versions=[
            EncounterVersionSummaryResponse(
                id=version.id,
                version_number=version.version_number,
                saved_at=version.saved_at,
            )
            for version in versions
        ],
    )


@router.patch("/{encounter_id}/draft", response_model=EncounterDraftResponse)
async def update_draft(
    payload: EncounterDraftUpdateRequest,
    encounter: Encounter = Depends(get_provider_owned_encounter),
    session: AsyncSession = Depends(get_database_session),
) -> EncounterDraftResponse:
    draft = await session.scalar(
        select(EncounterDraft).where(EncounterDraft.encounter_id == encounter.id)
    )
    if draft is not None and payload.base_revision is not None and payload.base_revision != draft.draft_revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Draft revision conflict.",
                "latest_draft": serialize_draft(draft, encounter.id).model_dump(mode="json"),
            },
        )

    if draft is None:
        draft = EncounterDraft(encounter_id=encounter.id, draft_revision=1)
        session.add(draft)
        await session.flush()

    for field in (
        "transcript",
        "observations",
        "subjective",
        "objective",
        "assessment",
        "plan",
        "selected_icd10_codes",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(draft, field, value)

    encounter.updated_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(draft)
    await AuditService.log_event(
        session,
        action="DRAFT_UPDATED",
        entity_type="encounter",
        entity_id=encounter.id,
        actor_user_id=encounter.provider_id,
        metadata_json={"draft_revision": draft.draft_revision},
    )
    await session.commit()
    return serialize_draft(draft, encounter.id)


@router.post("/{encounter_id}/generate")
async def generate_note(
    request: Request,
    encounter: Encounter = Depends(get_provider_owned_encounter),
    session: AsyncSession = Depends(get_database_session),
    note_generation_service: NoteGenerationService = Depends(get_note_generation_service),
) -> StreamingResponse:
    async def event_stream():
        yield format_sse_event(
            "generation_started",
            {"encounter_id": encounter.id, "status": "starting"},
        )

        try:
            result, draft = await note_generation_service.generate_for_encounter(
                session,
                encounter=encounter,
            )

            for section_name, section_value in (
                ("subjective", result.subjective),
                ("objective", result.objective),
                ("assessment", note_generation_service._format_assessment_for_ui(result)),
                ("plan", result.plan),
            ):
                for chunk in chunk_text(section_value):
                    if await request.is_disconnected():
                        return
                    yield format_sse_event(
                        "section_delta",
                        {"section": section_name, "text": chunk},
                    )
                    await asyncio.sleep(0)

            for item in result.assessment:
                if await request.is_disconnected():
                    return
                yield format_sse_event(
                    "assessment_code",
                    {
                        "diagnosis": item.diagnosis,
                        "code": item.icd10_code,
                        "description": item.description,
                    },
                )

            for warning in result.warnings:
                if await request.is_disconnected():
                    return
                yield format_sse_event("warning", {"message": warning})

            yield format_sse_event(
                "draft_saved",
                {
                    "draft_revision": draft.draft_revision,
                    "updated_at": draft.updated_at.isoformat(),
                },
            )
            yield format_sse_event(
                "generation_complete",
                {
                    "missing_information": result.missing_information,
                    "warnings": result.warnings,
                },
            )
        except InsufficientClinicalContentError as exc:
            yield format_sse_event(
                "generation_error",
                {
                    "code": "insufficient_clinical_content",
                    "message": str(exc),
                },
            )
        except AiClientError as exc:
            yield format_sse_event(
                "generation_error",
                {
                    "code": "ai_provider_error",
                    "message": str(exc),
                },
            )
        except Exception as exc:
            logger.exception("SOAP note generation failed: %s", exc)

            yield format_sse_event(
                "generation_error",
                {
                    "code": "generation_failed",
                    "message": "Unable to generate the SOAP note right now.",
                },
            )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{encounter_id}/save", response_model=SaveEncounterNoteResponse)
async def save_note(
    payload: SaveEncounterNoteRequest,
    encounter: Encounter = Depends(get_provider_owned_encounter),
    current_user=Depends(require_provider),
    session: AsyncSession = Depends(get_database_session),
) -> SaveEncounterNoteResponse:
    if not any(
        (value or "").strip()
        for value in [payload.subjective, payload.objective, payload.assessment, payload.plan]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one SOAP section must contain content before saving.",
        )

    try:
        note = await session.scalar(select(Note).where(Note.encounter_id == encounter.id))
        if note is None:
            note = Note(encounter_id=encounter.id)
            session.add(note)
            await session.flush()

        existing_versions = (
            await session.scalars(
                select(NoteVersion)
                .where(NoteVersion.note_id == note.id)
                .order_by(NoteVersion.version_number.desc())
            )
        ).all()

        for existing_version in existing_versions:
            metadata = existing_version.generation_metadata or {}
            if metadata.get("idempotency_key") == payload.idempotency_key:
                return SaveEncounterNoteResponse(
                    note_id=note.id,
                    version_id=existing_version.id,
                    version_number=existing_version.version_number,
                    encounter_status=encounter.status,
                )

        latest_version_number = existing_versions[0].version_number if existing_versions else 0
        next_version_number = latest_version_number + 1

        generation_metadata = dict(payload.generation_metadata or {})
        generation_metadata["idempotency_key"] = payload.idempotency_key

        version = NoteVersion(
            note_id=note.id,
            version_number=next_version_number,
            saved_by_user_id=current_user.id,
            subjective=payload.subjective,
            objective=payload.objective,
            assessment=payload.assessment,
            plan=payload.plan,
            icd10_codes=payload.icd10_codes,
            generation_metadata=generation_metadata,
        )
        session.add(version)
        await session.flush()

        note.current_version_id = version.id
        encounter.status = EncounterStatus.COMPLETED
        encounter.updated_at = datetime.now(UTC)
        await AuditService.log_event(
            session,
            actor_user_id=current_user.id,
            action="NOTE_VERSION_SAVED",
            entity_type="note",
            entity_id=note.id,
            metadata_json={
                "encounter_id": encounter.id,
                "version_id": version.id,
                "version_number": version.version_number,
                "idempotency_key": payload.idempotency_key,
            },
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(encounter)
    return SaveEncounterNoteResponse(
        note_id=note.id,
        version_id=version.id,
        version_number=version.version_number,
        encounter_status=encounter.status,
    )
