from fastapi import APIRouter

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("/status")
async def templates_status() -> dict[str, str]:
    return {"status": "not_implemented"}
