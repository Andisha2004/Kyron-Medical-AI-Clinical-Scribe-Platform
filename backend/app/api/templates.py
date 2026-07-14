from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_database_session, require_admin, require_provider
from app.db.models.encounter import Encounter
from app.db.models.enums import TemplateSectionType
from app.db.models.template import Template
from app.db.models.template_section import TemplateSection
from app.db.models.user import User
from app.schemas.template import (
    TemplateListResponse,
    TemplateMutationRequest,
    TemplateSectionInput,
    TemplateSectionResponse,
)
from app.services.audit_service import AuditService

router = APIRouter(tags=["templates"])


def serialize_template(template: Template) -> TemplateListResponse:
    return TemplateListResponse(
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

    return [serialize_template(template) for template in templates]


@router.get("/admin/templates", response_model=list[TemplateListResponse])
async def list_admin_templates(
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_database_session),
) -> list[TemplateListResponse]:
    templates = (
        await session.scalars(
            select(Template)
            .where(Template.deleted_at.is_(None))
            .options(selectinload(Template.sections))
            .order_by(Template.updated_at.desc(), Template.name.asc())
        )
    ).unique().all()
    return [serialize_template(template) for template in templates]


def _build_sections(
    payload_sections: list[TemplateSectionInput],
) -> list[TemplateSection]:
    built_sections: list[TemplateSection] = []
    seen_sections: set[str] = set()
    for section_payload in payload_sections:
        section_value = section_payload.section.lower()
        if section_value in seen_sections:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate template section: {section_payload.section}",
            )
        seen_sections.add(section_value)
        built_sections.append(
            TemplateSection(
                section=TemplateSectionType(section_value),
                instructions=section_payload.instructions.strip(),
                sort_order=section_payload.sort_order,
            )
        )
    return built_sections


@router.post("/admin/templates", response_model=TemplateListResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateMutationRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_database_session),
) -> TemplateListResponse:
    existing = await session.scalar(select(Template).where(Template.name == payload.name.strip()))
    if existing is not None and existing.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template name is already in use.")

    template = Template(
        name=payload.name.strip(),
        description=payload.description,
        is_active=payload.is_active,
        created_by_user_id=current_user.id,
    )
    template.sections = _build_sections(payload.sections)
    session.add(template)
    await session.flush()
    await AuditService.log_event(
        session,
        actor_user_id=current_user.id,
        action="TEMPLATE_CREATED",
        entity_type="template",
        entity_id=template.id,
        metadata={"name": template.name},
    )
    await session.commit()
    await session.refresh(template, ["sections"])
    return serialize_template(template)


@router.put("/admin/templates/{template_id}", response_model=TemplateListResponse)
async def update_template(
    template_id: str,
    payload: TemplateMutationRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_database_session),
) -> TemplateListResponse:
    template = await session.scalar(
        select(Template)
        .where(Template.id == template_id, Template.deleted_at.is_(None))
        .options(selectinload(Template.sections))
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

    duplicate = await session.scalar(
        select(Template).where(
            Template.name == payload.name.strip(),
            Template.id != template_id,
            Template.deleted_at.is_(None),
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Template name is already in use.")

    template.name = payload.name.strip()
    template.description = payload.description
    template.is_active = payload.is_active
    template.updated_at = datetime.now(UTC)
    template.sections.clear()
    await session.flush()
    template.sections.extend(_build_sections(payload.sections))

    await AuditService.log_event(
        session,
        actor_user_id=current_user.id,
        action="TEMPLATE_UPDATED",
        entity_type="template",
        entity_id=template.id,
        metadata={"name": template.name, "is_active": template.is_active},
    )
    await session.commit()
    await session.refresh(template, ["sections"])
    return serialize_template(template)


@router.delete("/admin/templates/{template_id}", response_model=TemplateListResponse)
async def delete_template(
    template_id: str,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_database_session),
) -> TemplateListResponse:
    template = await session.scalar(
        select(Template)
        .where(Template.id == template_id, Template.deleted_at.is_(None))
        .options(selectinload(Template.sections), selectinload(Template.encounters))
    )
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")

    # Protect existing encounter references by soft-deactivating instead of deleting rows.
    template.is_active = False
    template.deleted_at = datetime.now(UTC)
    template.updated_at = datetime.now(UTC)

    await AuditService.log_event(
        session,
        actor_user_id=current_user.id,
        action="TEMPLATE_DELETED",
        entity_type="template",
        entity_id=template.id,
        metadata={"name": template.name, "encounter_count": len(template.encounters)},
    )
    await session.commit()
    await session.refresh(template, ["sections"])
    return serialize_template(template)


@router.get("/admin/templates/status")
async def templates_status(_: str = Depends(require_admin)) -> dict[str, str]:
    return {"status": "admin_authenticated"}
