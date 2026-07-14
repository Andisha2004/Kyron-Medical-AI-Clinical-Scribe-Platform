import { api } from "@/lib/api";
import type {
  DictationSegmentRequest,
  DictationSegmentResponse,
  DictationSessionResponse,
  VoiceCommandRequest,
  VoiceCommandResponse,
  VoiceSessionResponse,
} from "@/types/voice";

export async function createDictationSession(
  encounterId: string,
): Promise<DictationSessionResponse> {
  return api.post<DictationSessionResponse>(
    `/api/voice/encounters/${encounterId}/dictation/session`,
  );
}

export async function processDictationSegment(
  encounterId: string,
  payload: DictationSegmentRequest,
): Promise<DictationSegmentResponse> {
  return api.post<DictationSegmentResponse>(
    `/api/voice/encounters/${encounterId}/dictation/segments`,
    payload,
  );
}

export async function createVoiceSession(encounterId: string): Promise<VoiceSessionResponse> {
  return api.post<VoiceSessionResponse>(`/api/voice/encounters/${encounterId}/session`);
}

export async function applyVoiceCommand(
  encounterId: string,
  payload: VoiceCommandRequest,
): Promise<VoiceCommandResponse> {
  return api.post<VoiceCommandResponse>(`/api/voice/encounters/${encounterId}/commands`, payload);
}
