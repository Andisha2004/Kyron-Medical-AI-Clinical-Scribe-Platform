from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_database_session, require_admin, require_provider
from app.db.models.template import Template
from app.db.models.user import User
from app.schemas.template import TemplateListResponse, TemplateSectionResponse

router = APIRouter(tags=["templates"])


@router.get("/templates", response_model=list[TemplateListResponse])
async def list_active_templates(
    _: User = Depends(require_provider),
    session: AsyncSession = Depends(get_database_session),
) -> list[TemplateListResponse]:
    result = await session.scalars(
        select(Template)
        .where(Template.is_active.is_(True), Template.deleted_at.is_(None))
        .options(selectinload(Template.sections))
        .order_by(Template.name.asc())
    )
    templates = result.unique().all()

    return [
        TemplateListResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            is_active=template.is_active,
            sections=[
                TemplateSectionResponse(
                    id=section.id,
                    section=section.section.value,
                    instructions=section.instructions,
                    sort_order=section.sort_order,
                )
                for section in sorted(template.sections, key=lambda item: (item.sort_order, item.section.value))
            ],
        )
        for template in templates
    ]


@router.get("/admin/templates/status")
async def templates_status(_: str = Depends(require_admin)) -> dict[str, str]:
    return {"status": "admin_authenticated"}
