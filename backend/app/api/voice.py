from fastapi import APIRouter, Depends

from app.api.dependencies import get_provider_owned_encounter

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/encounters/{encounter_id}/dictation/status")
async def dictation_status(encounter=Depends(get_provider_owned_encounter)) -> dict[str, str]:
    return {"status": "provider_owned_encounter_verified", "encounter_id": encounter.id}


@router.get("/encounters/{encounter_id}/voice-edit/status")
async def voice_edit_status(encounter=Depends(get_provider_owned_encounter)) -> dict[str, str]:
    return {"status": "provider_owned_encounter_verified", "encounter_id": encounter.id}
