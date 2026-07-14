from fastapi import APIRouter

router = APIRouter(prefix="/icd", tags=["icd"])


@router.get("/status")
async def icd_status() -> dict[str, str]:
    return {"status": "not_implemented"}
