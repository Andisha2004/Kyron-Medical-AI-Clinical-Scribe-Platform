from fastapi import APIRouter, Depends

from app.api.dependencies import require_admin

router = APIRouter(prefix="/admin/providers", tags=["providers"])


@router.get("/status")
async def providers_status(_: str = Depends(require_admin)) -> dict[str, str]:
    return {"status": "admin_authenticated"}
