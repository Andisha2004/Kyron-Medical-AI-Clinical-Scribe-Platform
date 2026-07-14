import type { EncounterDraftResponse } from "@/types/encounter";

export type SoapSection = "subjective" | "objective" | "assessment" | "plan";
export type VoiceOperationType =
  "append" | "replace" | "remove" | "move" | "shorten" | "rewrite_note";

export interface VoiceEditOperation {
  operation: VoiceOperationType;
  source_section?: SoapSection | null;
  target_section?: SoapSection | null;
  target_text?: string | null;
  new_text?: string | null;
}

export interface VoiceConversationTurn {
  role: "provider" | "assistant";
  text: string;
}

export interface VoiceCommandRequest {
  command: string;
  base_revision: number | null;
  conversation_history?: VoiceConversationTurn[];
}

export interface VoiceCommandResponse {
  applied: boolean;
  assistant_response: string;
  operation: VoiceEditOperation | null;
  updated_section: SoapSection | null;
  updated_text: string | null;
  draft_revision: number;
  draft: EncounterDraftResponse;
}

export interface VoiceSessionResponse {
  provider: string;
  connection_method: "webrtc" | "websocket" | "browser_speech_fallback";
  session_status: "ready" | "configured_locally_only" | "not_configured";
  model: string;
  voice: string;
  supports_browser_audio: boolean;
  supports_interruption: boolean;
  supports_tool_calls: boolean;
  supports_continuous_conversation: boolean;
  client_secret: string | null;
  websocket_url: string | null;
  message: string;
}

export interface DictationSessionResponse {
  provider: string;
  connection_method: "webrtc" | "websocket" | "browser_speech_fallback";
  session_status: "ready" | "configured_locally_only" | "not_configured";
  model: string;
  language: string;
  input_audio_format: string;
  sample_rate_hz: number;
  supports_partial_transcripts: boolean;
  supports_final_transcripts: boolean;
  supports_browser_audio: boolean;
  supports_reconnect: boolean;
  message: string;
}

export interface DictationPatchOperation {
  operation: "append";
  section: SoapSection;
  text: string;
}

export interface DictationSegmentRequest {
  transcript_segment: string;
  is_final: boolean;
  base_revision: number | null;
  segment_id?: string | null;
}

export interface DictationSegmentResponse {
  accepted: boolean;
  transcript_appended: boolean;
  transcript_preview: string;
  partial_transcript: string | null;
  operations: DictationPatchOperation[];
  draft_revision: number;
  draft: EncounterDraftResponse;
}
