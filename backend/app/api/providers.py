from fastapi import APIRouter

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/status")
async def providers_status() -> dict[str, str]:
    return {"status": "not_implemented"}
