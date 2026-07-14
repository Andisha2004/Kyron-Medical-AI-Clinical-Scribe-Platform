"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { applyVoiceCommand, createVoiceSession } from "@/lib/voice";
import type { DraftState } from "@/types/encounter";
import type { SpeechRecognitionLike } from "@/types/speech-recognition";
import type {
  VoiceCommandResponse,
  VoiceConversationTurn,
  VoiceSessionResponse,
} from "@/types/voice";

interface VoiceEditPanelProps {
  encounterId: string;
  draft: DraftState;
  baseRevision: number | null;
  onDraftApplied: (response: VoiceCommandResponse) => void;
  onError: (message: string | null) => void;
}

export function VoiceEditPanel({
  encounterId,
  draft,
  baseRevision,
  onDraftApplied,
  onError,
}: VoiceEditPanelProps) {
  const [voiceSession, setVoiceSession] = useState<VoiceSessionResponse | null>(null);
  const [isSessionStarting, setIsSessionStarting] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [manualCommand, setManualCommand] = useState("");
  const [assistantResponse, setAssistantResponse] = useState<string | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [conversationTurns, setConversationTurns] = useState<VoiceConversationTurn[]>([]);
  const [isSubmittingCommand, setIsSubmittingCommand] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const keepListeningRef = useRef(false);

  const speechRecognitionSupported =
    typeof window !== "undefined" &&
    (window.SpeechRecognition !== undefined || window.webkitSpeechRecognition !== undefined);

  useEffect(() => {
    return () => {
      keepListeningRef.current = false;
      recognitionRef.current?.stop();
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  function stopAssistantSpeech() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }

  function speakAssistantResponse(text: string) {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }

    stopAssistantSpeech();
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
  }

  async function submitCommand(command: string) {
    const normalizedCommand = command.trim();
    if (!normalizedCommand) {
      return;
    }

    stopAssistantSpeech();
    setInterimTranscript("");
    setIsSubmittingCommand(true);
    setVoiceError(null);
    onError(null);
    setConversationTurns((current) => [...current, { role: "provider", text: normalizedCommand }]);

    try {
      const response = await applyVoiceCommand(encounterId, {
        command: normalizedCommand,
        base_revision: baseRevision,
        conversation_history: conversationTurns,
      });
      onDraftApplied(response);
      setAssistantResponse(response.assistant_response);
      setConversationTurns((current) => [
        ...current,
        { role: "assistant", text: response.assistant_response },
      ]);
      speakAssistantResponse(response.assistant_response);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Unable to apply the voice command.";
      setVoiceError(message);
      onError(message);
    } finally {
      setIsSubmittingCommand(false);
    }
  }

  async function startVoiceEditing() {
    setIsSessionStarting(true);
    setVoiceError(null);
    onError(null);

    try {
      const session = await createVoiceSession(encounterId);
      setVoiceSession(session);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Unable to initialize the voice session.";
      setVoiceError(message);
      onError(message);
      setIsSessionStarting(false);
      return;
    }

    if (!speechRecognitionSupported) {
      setVoiceError(
        "Browser speech recognition is not available here. You can still use the manual command box below.",
      );
      setIsSessionStarting(false);
      return;
    }

    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
    if (!Recognition) {
      setVoiceError(
        "Browser speech recognition is not available here. You can still use the manual command box below.",
      );
      setIsSessionStarting(false);
      return;
    }

    if (!recognitionRef.current) {
      const recognition = new Recognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onend = () => {
        setIsListening(false);
        if (keepListeningRef.current) {
          recognition.start();
        }
      };

      recognition.onerror = (event) => {
        if (event.error === "not-allowed") {
          setVoiceError("Microphone access was denied.");
        } else {
          setVoiceError(`Voice recognition error${event.error ? `: ${event.error}` : "."}`);
        }
      };

      recognition.onresult = (event) => {
        let latestInterim = "";

        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const result = event.results[index];
          const transcript = Array.from(result)
            .map((item) => item.transcript)
            .join("")
            .trim();

          if (!transcript) {
            continue;
          }

          if (result.isFinal) {
            void submitCommand(transcript);
          } else {
            latestInterim = transcript;
          }
        }

        setInterimTranscript(latestInterim);
      };

      recognitionRef.current = recognition;
    }

    keepListeningRef.current = true;
    recognitionRef.current?.start();
    setIsSessionStarting(false);
  }

  function stopVoiceEditing() {
    keepListeningRef.current = false;
    recognitionRef.current?.stop();
    stopAssistantSpeech();
    setIsListening(false);
    setInterimTranscript("");
  }

  const draftSummary = [
    draft.subjective ? "Subjective loaded" : null,
    draft.objective ? "Objective loaded" : null,
    draft.assessment ? "Assessment loaded" : null,
    draft.plan ? "Plan loaded" : null,
  ]
    .filter(Boolean)
    .join(" • ");

  return (
    <div className="space-y-4" data-testid="voice-edit-panel">
      <div className="flex flex-wrap gap-3">
        <Button
          variant="secondary"
          onClick={() => void startVoiceEditing()}
          disabled={isSessionStarting || isListening}
          data-testid="voice-start-button"
        >
          {isSessionStarting ? "Starting..." : "Start voice editing"}
        </Button>
        <Button
          variant="secondary"
          onClick={stopVoiceEditing}
          disabled={!isListening}
          data-testid="voice-stop-button"
        >
          Stop voice editing
        </Button>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-800">Session status</p>
          <p className="mt-2 text-sm text-slate-600">
            {voiceSession?.message ??
              "Voice editing is not configured yet. You can still test note edits with the manual command box."}
          </p>
          <p
            className="mt-2 text-xs text-slate-500"
            role="status"
            aria-live="polite"
            data-testid="voice-status"
          >
            {isListening ? "Listening now." : "Not listening."}
            {draftSummary ? ` ${draftSummary}.` : ""}
          </p>
          {interimTranscript ? (
            <p
              className="mt-3 rounded-md bg-white px-3 py-2 text-sm text-slate-700"
              data-testid="voice-interim-transcript"
              role="status"
              aria-live="polite"
            >
              Interim: {interimTranscript}
            </p>
          ) : null}
          {assistantResponse ? (
            <p
              className="mt-3 rounded-md bg-white px-3 py-2 text-sm text-slate-700"
              data-testid="voice-assistant-response"
              role="status"
              aria-live="polite"
            >
              Assistant: {assistantResponse}
            </p>
          ) : null}
          {voiceError ? (
            <p
              className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
              data-testid="voice-error"
            >
              {voiceError}
            </p>
          ) : null}
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <label htmlFor="voice-command" className="block text-sm font-semibold text-slate-800">
            Enter a command manually
          </label>
          <textarea
            id="voice-command"
            data-testid="voice-command-input"
            rows={4}
            value={manualCommand}
            onChange={(event) => setManualCommand(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
            placeholder="Add that the patient denies fever."
          />
          <div className="mt-3 flex flex-wrap gap-3">
            <Button
              onClick={() => {
                void submitCommand(manualCommand);
                setManualCommand("");
              }}
              disabled={isSubmittingCommand || manualCommand.trim().length < 3}
              data-testid="voice-apply-command-button"
            >
              {isSubmittingCommand ? "Applying..." : "Apply command"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => setManualCommand("Shorten the Plan")}
              disabled={isSubmittingCommand}
            >
              Try &quot;Shorten the Plan&quot;
            </Button>
          </div>
        </div>
      </div>

      <div
        className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4"
        data-testid="voice-conversation-panel"
      >
        <p className="text-sm font-semibold text-slate-800">Conversation transcript</p>
        {conversationTurns.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">
            Start voice editing or submit a manual command to begin the conversation.
          </p>
        ) : (
          <div className="mt-3 space-y-3">
            {conversationTurns.map((turn, index) => (
              <div
                key={`${turn.role}-${index}`}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2"
              >
                <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
                  {turn.role === "provider" ? "Provider" : "Assistant"}
                </p>
                <p className="mt-1 text-sm text-slate-800">{turn.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
