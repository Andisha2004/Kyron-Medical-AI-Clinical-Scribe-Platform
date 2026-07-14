from fastapi import APIRouter

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/status")
async def notes_status() -> dict[str, str]:
    return {"status": "not_implemented"}
