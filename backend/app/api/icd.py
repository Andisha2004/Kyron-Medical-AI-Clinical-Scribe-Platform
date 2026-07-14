from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database_session, require_authenticated_user
from app.schemas.icd import IcdSearchResultResponse
from app.services.icd_service import IcdService

router = APIRouter(prefix="/icd", tags=["icd"])

icd_service = IcdService()


@router.get("/status")
async def icd_status() -> dict[str, str]:
    return {"status": icd_service.service_status()}


@router.get("/search", response_model=list[IcdSearchResultResponse])
async def search_icd_codes(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=20),
    _: object = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_database_session),
) -> list[IcdSearchResultResponse]:
    normalized_query = q.strip()
    if not normalized_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Search query cannot be empty.",
        )

    results = await icd_service.search_codes(session, normalized_query, limit=limit)
    return [
        IcdSearchResultResponse(
            code=result.code,
            description=result.description,
            category=result.category,
            score=result.score,
        )
        for result in results
    ]
