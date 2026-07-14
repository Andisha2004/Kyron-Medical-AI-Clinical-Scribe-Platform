from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.encounter import EncounterDraftResponse

SoapSection = Literal["subjective", "objective", "assessment", "plan"]
VoiceOperationType = Literal["append", "replace", "remove", "move", "shorten", "rewrite_note"]


class VoiceConversationTurn(BaseModel):
    role: Literal["provider", "assistant"]
    text: str = Field(min_length=1, max_length=500)


class VoiceEditOperation(BaseModel):
    operation: VoiceOperationType
    source_section: SoapSection | None = None
    target_section: SoapSection | None = None
    target_text: str | None = None
    new_text: str | None = None

    @model_validator(mode="after")
    def validate_operation_fields(self) -> "VoiceEditOperation":
        if self.operation == "append":
            if not self.target_section or not self.new_text:
                raise ValueError("Append operations require target_section and new_text.")
        elif self.operation == "replace":
            if not self.target_section or not self.target_text or not self.new_text:
                raise ValueError(
                    "Replace operations require target_section, target_text, and new_text."
                )
        elif self.operation == "remove":
            if not self.target_section or not self.target_text:
                raise ValueError("Remove operations require target_section and target_text.")
        elif self.operation == "move":
            if not self.source_section or not self.target_section or not self.target_text:
                raise ValueError(
                    "Move operations require source_section, target_section, and target_text."
                )
            if self.source_section == self.target_section:
                raise ValueError("Move operations require different source and target sections.")
        elif self.operation == "shorten":
            if not self.target_section:
                raise ValueError("Shorten operations require target_section.")
        elif self.operation == "rewrite_note":
            return self

        for field_name in ("target_text", "new_text"):
            value = getattr(self, field_name)
            if value and ("<" in value or ">" in value):
                raise ValueError(f"{field_name} cannot contain HTML or code-like markup.")

        return self


class VoiceCommandRequest(BaseModel):
    command: str = Field(min_length=3, max_length=500)
    base_revision: int | None = None
    conversation_history: list[VoiceConversationTurn] = Field(default_factory=list)


class VoiceCommandResponse(BaseModel):
    applied: bool
    assistant_response: str
    operation: VoiceEditOperation | None = None
    updated_section: SoapSection | None = None
    updated_text: str | None = None
    draft_revision: int
    draft: EncounterDraftResponse


class VoiceRewriteResult(BaseModel):
    subjective: str
    objective: str
    assessment: str
    plan: str
    assistant_response: str


class VoiceSessionResponse(BaseModel):
    provider: str
    connection_method: Literal["webrtc", "websocket", "browser_speech_fallback"]
    session_status: Literal["ready", "configured_locally_only", "not_configured"]
    model: str
    voice: str
    supports_browser_audio: bool
    supports_interruption: bool
    supports_tool_calls: bool
    supports_continuous_conversation: bool
    client_secret: str | None = None
    websocket_url: str | None = None
    message: str


class DictationSessionResponse(BaseModel):
    provider: str
    connection_method: Literal["webrtc", "websocket", "browser_speech_fallback"]
    session_status: Literal["ready", "configured_locally_only", "not_configured"]
    model: str
    language: str
    input_audio_format: str
    sample_rate_hz: int
    supports_partial_transcripts: bool
    supports_final_transcripts: bool
    supports_browser_audio: bool
    supports_reconnect: bool
    message: str


class DictationPatchOperation(BaseModel):
    operation: Literal["append"]
    section: SoapSection
    text: str = Field(min_length=1)


class DictationSegmentRequest(BaseModel):
    transcript_segment: str = Field(min_length=1, max_length=1000)
    is_final: bool = True
    base_revision: int | None = None
    segment_id: str | None = Field(default=None, max_length=120)


class DictationSegmentResponse(BaseModel):
    accepted: bool
    transcript_appended: bool
    transcript_preview: str
    partial_transcript: str | None = None
    operations: list[DictationPatchOperation] = Field(default_factory=list)
    draft_revision: int
    draft: EncounterDraftResponse
