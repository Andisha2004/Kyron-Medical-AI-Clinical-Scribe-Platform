from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database_session, get_provider_owned_encounter, require_provider
from app.core.config import get_settings
from app.db.models.encounter import Encounter
from app.db.models.encounter_draft import EncounterDraft
from app.db.models.user import User
from app.schemas.encounter import EncounterDraftResponse
from app.schemas.voice import (
    DictationSegmentRequest,
    DictationSegmentResponse,
    DictationSessionResponse,
    VoiceCommandRequest,
    VoiceCommandResponse,
    VoiceSessionResponse,
)
from app.services.dictation_service import DictationService, get_dictation_service
from app.services.voice_edit_service import VoiceEditService, get_voice_edit_service

router = APIRouter(prefix="/voice", tags=["voice"])


def serialize_draft(draft: EncounterDraft, encounter_id: str) -> EncounterDraftResponse:
    return EncounterDraftResponse(
        encounter_id=encounter_id,
        transcript=draft.transcript,
        observations=draft.observations,
        subjective=draft.subjective,
        objective=draft.objective,
        assessment=draft.assessment,
        plan=draft.plan,
        selected_icd10_codes=draft.selected_icd10_codes or [],
        draft_revision=draft.draft_revision,
        updated_at=draft.updated_at,
    )


@router.get("/encounters/{encounter_id}/dictation/status")
async def dictation_status(encounter=Depends(get_provider_owned_encounter)) -> dict[str, str]:
    return {"status": "provider_owned_encounter_verified", "encounter_id": encounter.id}


@router.get("/encounters/{encounter_id}/voice-edit/status")
async def voice_edit_status(encounter=Depends(get_provider_owned_encounter)) -> dict[str, str]:
    return {"status": "provider_owned_encounter_verified", "encounter_id": encounter.id}


@router.post("/encounters/{encounter_id}/dictation/session", response_model=DictationSessionResponse)
async def create_dictation_session(
    encounter: Encounter = Depends(get_provider_owned_encounter),
    _: User = Depends(require_provider),
) -> DictationSessionResponse:
    settings = get_settings()
    api_key_configured = bool(settings.openai_api_key) and not settings.openai_api_key.startswith(
        "replace_with_"
    )

    return DictationSessionResponse(
        provider="openai_realtime",
        connection_method="browser_speech_fallback"
        if not settings.openai_realtime_create_remote_session
        else "webrtc",
        session_status="configured_locally_only" if api_key_configured else "not_configured",
        model=settings.openai_realtime_transcription_model,
        language=settings.openai_realtime_transcription_language,
        input_audio_format="audio/pcm",
        sample_rate_hz=24000,
        supports_partial_transcripts=True,
        supports_final_transcripts=True,
        supports_browser_audio=True,
        supports_reconnect=True,
        message=(
            f"Realtime dictation is configured for encounter {encounter.id}. "
            "The local UI can use browser speech recognition now and upgrade to OpenAI Realtime audio once the remote session path is enabled."
            if api_key_configured
            else "OpenAI Realtime transcription is selected but the API key is not configured yet."
        ),
    )


@router.post("/encounters/{encounter_id}/dictation/segments", response_model=DictationSegmentResponse)
async def process_dictation_segment(
    payload: DictationSegmentRequest,
    encounter: Encounter = Depends(get_provider_owned_encounter),
    current_user: User = Depends(require_provider),
    session: AsyncSession = Depends(get_database_session),
    dictation_service: DictationService = Depends(get_dictation_service),
) -> DictationSegmentResponse:
    result = await dictation_service.process_segment(
        session=session,
        encounter=encounter,
        payload=payload,
        actor_user_id=current_user.id,
    )

    return DictationSegmentResponse(
        accepted=result.accepted,
        transcript_appended=result.transcript_appended,
        transcript_preview=result.transcript_preview,
        partial_transcript=result.partial_transcript,
        operations=result.operations,
        draft_revision=result.draft.draft_revision,
        draft=serialize_draft(result.draft, encounter.id),
    )


@router.post("/encounters/{encounter_id}/session", response_model=VoiceSessionResponse)
async def create_voice_session(
    encounter: Encounter = Depends(get_provider_owned_encounter),
    _: User = Depends(require_provider),
) -> VoiceSessionResponse:
    settings = get_settings()
    api_key_configured = bool(settings.openai_api_key) and not settings.openai_api_key.startswith(
        "replace_with_"
    )

    if settings.voice_provider != "openai_realtime":
        return VoiceSessionResponse(
            provider=settings.voice_provider,
            connection_method="browser_speech_fallback",
            session_status="configured_locally_only",
            model=settings.openai_realtime_model,
            voice=settings.openai_realtime_voice,
            supports_browser_audio=True,
            supports_interruption=True,
            supports_tool_calls=True,
            supports_continuous_conversation=True,
            message="Voice provider is configured for local browser fallback mode.",
        )

    if api_key_configured and settings.openai_realtime_create_remote_session:
        return VoiceSessionResponse(
            provider="openai_realtime",
            connection_method="webrtc",
            session_status="ready",
            model=settings.openai_realtime_model,
            voice=settings.openai_realtime_voice,
            supports_browser_audio=True,
            supports_interruption=True,
            supports_tool_calls=True,
            supports_continuous_conversation=True,
            message=f"Realtime voice session is enabled for encounter {encounter.id}.",
        )

    return VoiceSessionResponse(
        provider="openai_realtime",
        connection_method="browser_speech_fallback",
        session_status="configured_locally_only" if api_key_configured else "not_configured",
        model=settings.openai_realtime_model,
        voice=settings.openai_realtime_voice,
        supports_browser_audio=True,
        supports_interruption=True,
        supports_tool_calls=True,
        supports_continuous_conversation=True,
        message=(
            "OpenAI Realtime is selected. The backend is configured to keep secrets server-side, "
            "and the frontend can use browser speech fallback for local development."
            if api_key_configured
            else "OpenAI Realtime is selected but the API key is not configured yet."
        ),
    )


@router.post("/encounters/{encounter_id}/commands", response_model=VoiceCommandResponse)
async def apply_voice_command(
    payload: VoiceCommandRequest,
    encounter: Encounter = Depends(get_provider_owned_encounter),
    current_user: User = Depends(require_provider),
    session: AsyncSession = Depends(get_database_session),
    voice_edit_service: VoiceEditService = Depends(get_voice_edit_service),
) -> VoiceCommandResponse:
    result = await voice_edit_service.apply_voice_command(
        session=session,
        encounter=encounter,
        payload=payload,
        actor_user_id=current_user.id,
    )

    refreshed_draft = await session.scalar(
        select(EncounterDraft).where(EncounterDraft.encounter_id == encounter.id)
    )
    assert refreshed_draft is not None

    return VoiceCommandResponse(
        applied=True,
        assistant_response=result.assistant_response,
        operation=result.operation,
        updated_section=result.updated_section,
        updated_text=result.updated_text,
        draft_revision=refreshed_draft.draft_revision,
        draft=serialize_draft(refreshed_draft, encounter.id),
    )
