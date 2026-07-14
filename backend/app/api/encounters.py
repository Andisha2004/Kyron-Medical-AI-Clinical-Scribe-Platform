from fastapi import APIRouter

router = APIRouter(prefix="/encounters", tags=["encounters"])


@router.get("/status")
async def encounters_status() -> dict[str, str]:
    return {"status": "not_implemented"}
