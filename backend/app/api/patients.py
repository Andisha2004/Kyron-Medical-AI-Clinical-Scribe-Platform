from fastapi import APIRouter

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/status")
async def patients_status() -> dict[str, str]:
    return {"status": "not_implemented"}
