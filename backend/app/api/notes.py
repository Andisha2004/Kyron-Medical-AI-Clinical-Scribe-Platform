from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import (
    get_accessible_note,
    get_database_session,
    require_authenticated_user,
)
from app.db.models.note import Note
from app.db.models.note_version import NoteVersion
from app.db.models.user import User
from app.schemas.note import NoteVersionResponse, SavedByUserSummary

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/status")
async def notes_status(_: User = Depends(require_authenticated_user)) -> dict[str, str]:
    return {"status": "authenticated"}


@router.get("/{note_id}/versions", response_model=list[NoteVersionResponse])
async def get_note_versions(
    note: Note = Depends(get_accessible_note),
    session: AsyncSession = Depends(get_database_session),
) -> list[NoteVersionResponse]:
    versions = (
        await session.scalars(
            select(NoteVersion)
            .where(NoteVersion.note_id == note.id)
            .options(selectinload(NoteVersion.saved_by_user).selectinload(User.provider_profile))
            .order_by(NoteVersion.version_number.desc())
        )
    ).all()
    return [
        NoteVersionResponse(
            id=version.id,
            note_id=version.note_id,
            version_number=version.version_number,
            saved_by_user_id=version.saved_by_user_id,
            saved_by_user=SavedByUserSummary(
                id=version.saved_by_user.id,
                email=version.saved_by_user.email,
                first_name=version.saved_by_user.provider_profile.first_name if version.saved_by_user.provider_profile else None,
                last_name=version.saved_by_user.provider_profile.last_name if version.saved_by_user.provider_profile else None,
            ),
            subjective=version.subjective,
            objective=version.objective,
            assessment=version.assessment,
            plan=version.plan,
            icd10_codes=version.icd10_codes,
            saved_at=version.saved_at,
            generation_metadata=version.generation_metadata,
        )
        for version in versions
    ]
