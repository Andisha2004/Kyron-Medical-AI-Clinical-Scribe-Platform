from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_database_session, require_admin
from app.core.security import hash_password
from app.db.models.encounter import Encounter
from app.db.models.enums import UserRole
from app.db.models.provider_profile import ProviderProfile
from app.db.models.template import Template
from app.db.models.user import User
from app.schemas.admin import (
    AdminDashboardEncounterResponse,
    AdminDashboardResponse,
    AdminProviderSummaryResponse,
    CreateProviderRequest,
    ProviderStatusUpdateRequest,
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin", tags=["admin"])


def build_provider_summary(user: User) -> AdminProviderSummaryResponse:
    profile = user.provider_profile
    if profile is None:
        raise ValueError("Provider profile is required for provider users.")

    return AdminProviderSummaryResponse(
        id=user.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=user.email,
        specialty=profile.specialty,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_database_session),
) -> AdminDashboardResponse:
    active_provider_count = await session.scalar(
        select(func.count(User.id)).where(User.role == UserRole.PROVIDER, User.is_active.is_(True))
    )
    total_encounter_count = await session.scalar(select(func.count(Encounter.id)))
    active_template_count = await session.scalar(
        select(func.count(Template.id)).where(Template.is_active.is_(True), Template.deleted_at.is_(None))
    )

    recent_encounters = (
        await session.scalars(
            select(Encounter)
            .options(
                selectinload(Encounter.patient),
                selectinload(Encounter.provider).selectinload(User.provider_profile),
                selectinload(Encounter.template),
            )
            .order_by(Encounter.updated_at.desc(), Encounter.encounter_date.desc())
            .limit(5)
        )
    ).unique().all()

    return AdminDashboardResponse(
        active_provider_count=active_provider_count or 0,
        total_encounter_count=total_encounter_count or 0,
        active_template_count=active_template_count or 0,
        recent_encounters=[
            AdminDashboardEncounterResponse(
                id=encounter.id,
                patient_name=f"{encounter.patient.first_name} {encounter.patient.last_name}",
                provider_name=(
                    f"{encounter.provider.provider_profile.first_name} {encounter.provider.provider_profile.last_name}"
                    if encounter.provider.provider_profile
                    else encounter.provider.email
                ),
                status=encounter.status.value,
                encounter_date=encounter.encounter_date,
                template_name=encounter.template.name,
            )
            for encounter in recent_encounters
        ],
    )


@router.get("/providers", response_model=list[AdminProviderSummaryResponse])
async def list_providers(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_database_session),
) -> list[AdminProviderSummaryResponse]:
    providers = (
        await session.scalars(
            select(User)
            .where(User.role == UserRole.PROVIDER)
            .options(selectinload(User.provider_profile))
            .order_by(User.created_at.desc(), User.email.asc())
        )
    ).unique().all()

    return [build_provider_summary(provider) for provider in providers if provider.provider_profile]


@router.post("/providers", response_model=AdminProviderSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    payload: CreateProviderRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_database_session),
) -> AdminProviderSummaryResponse:
    normalized_email = payload.email.lower()
    existing_user = await session.scalar(select(User).where(User.email == normalized_email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already in use.")

    provider = User(
        email=normalized_email,
        password_hash=hash_password(payload.password),
        role=UserRole.PROVIDER,
        is_active=True,
    )
    provider.provider_profile = ProviderProfile(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        specialty=payload.specialty.strip() if payload.specialty else None,
    )
    session.add(provider)
    await session.flush()

    await AuditService.log_event(
        session,
        actor_user_id=current_user.id,
        action="PROVIDER_CREATED",
        entity_type="user",
        entity_id=provider.id,
        metadata={
            "email": provider.email,
            "specialty": provider.provider_profile.specialty,
        },
    )
    await session.commit()
    await session.refresh(provider, ["provider_profile"])
    return build_provider_summary(provider)


@router.patch("/providers/{provider_id}/status", response_model=AdminProviderSummaryResponse)
async def update_provider_status(
    provider_id: str,
    payload: ProviderStatusUpdateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_database_session),
) -> AdminProviderSummaryResponse:
    provider = await session.scalar(
        select(User)
        .where(User.id == provider_id, User.role == UserRole.PROVIDER)
        .options(selectinload(User.provider_profile))
    )
    if provider is None or provider.provider_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")

    provider.is_active = payload.is_active
    provider.updated_at = datetime.now(UTC)
    await AuditService.log_event(
        session,
        actor_user_id=current_user.id,
        action="PROVIDER_REACTIVATED" if payload.is_active else "PROVIDER_DEACTIVATED",
        entity_type="user",
        entity_id=provider.id,
        metadata={"is_active": payload.is_active},
    )
    await session.commit()
    await session.refresh(provider, ["provider_profile"])
    return build_provider_summary(provider)


@router.get("/providers/status")
async def providers_status(_: User = Depends(require_admin)) -> dict[str, str]:
    return {"status": "admin_authenticated"}
