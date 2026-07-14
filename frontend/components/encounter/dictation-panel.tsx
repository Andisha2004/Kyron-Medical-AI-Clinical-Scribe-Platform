"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { createDictationSession, processDictationSegment } from "@/lib/voice";
import type { EncounterDraftResponse } from "@/types/encounter";
import type { SpeechRecognitionLike } from "@/types/speech-recognition";
import type { DictationSessionResponse } from "@/types/voice";

type DictationState = "idle" | "starting" | "listening" | "paused" | "stopping";

interface DictationPanelProps {
  encounterId: string;
  baseRevision: number | null;
  onDraftApplied: (response: { draft: EncounterDraftResponse; draft_revision: number }) => void;
  onError: (message: string | null) => void;
}

interface PendingSegment {
  id: string;
  text: string;
}

function normalizeTranscript(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

export function DictationPanel({
  encounterId,
  baseRevision,
  onDraftApplied,
  onError,
}: DictationPanelProps) {
  const [dictationState, setDictationState] = useState<DictationState>("idle");
  const [sessionInfo, setSessionInfo] = useState<DictationSessionResponse | null>(null);
  const [partialTranscript, setPartialTranscript] = useState("");
  const [finalSegments, setFinalSegments] = useState<string[]>([]);
  const [dictationError, setDictationError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState("Not started.");
  const [manualSegment, setManualSegment] = useState("");
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const keepListeningRef = useRef(false);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const pendingSegmentsRef = useRef<PendingSegment[]>([]);
  const isProcessingQueueRef = useRef(false);
  const baseRevisionRef = useRef<number | null>(baseRevision);

  const speechRecognitionSupported =
    typeof window !== "undefined" &&
    (window.SpeechRecognition !== undefined || window.webkitSpeechRecognition !== undefined);

  useEffect(() => {
    baseRevisionRef.current = baseRevision;
  }, [baseRevision]);

  useEffect(() => {
    return () => {
      keepListeningRef.current = false;
      recognitionRef.current?.stop();
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  function stopMicrophoneTracks() {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
  }

  async function ensureMicrophoneAccess(): Promise<void> {
    if (mediaStreamRef.current) {
      return;
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    stream.getAudioTracks().forEach((track) => {
      track.addEventListener("ended", () => {
        setDictationError("The microphone input was disconnected.");
        onError("The microphone input was disconnected.");
        keepListeningRef.current = false;
        setDictationState("paused");
      });
    });

    mediaStreamRef.current = stream;
  }

  function setError(message: string | null) {
    setDictationError(message);
    onError(message);
  }

  async function flushPendingSegments() {
    if (isProcessingQueueRef.current) {
      return;
    }

    isProcessingQueueRef.current = true;
    setIsSyncing(true);

    try {
      while (pendingSegmentsRef.current.length > 0) {
        const nextSegment = pendingSegmentsRef.current[0];
        setSyncStatus(`Synchronizing finalized segment: "${nextSegment.text}"`);

        const response = await processDictationSegment(encounterId, {
          transcript_segment: nextSegment.text,
          is_final: true,
          base_revision: baseRevisionRef.current,
          segment_id: nextSegment.id,
        });

        pendingSegmentsRef.current.shift();
        baseRevisionRef.current = response.draft_revision;
        onDraftApplied({
          draft: response.draft,
          draft_revision: response.draft_revision,
        });
        setLastSyncedAt(new Date().toISOString());

        if (pendingSegmentsRef.current.length > 0) {
          setSyncStatus(
            `${pendingSegmentsRef.current.length} finalized segment${pendingSegmentsRef.current.length === 1 ? "" : "s"} waiting to sync.`,
          );
        }
      }

      setSyncStatus("Transcript synchronized.");
      setError(null);
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Unable to synchronize dictation updates.";
      setError(message);
      setSyncStatus("Synchronization failed.");
    } finally {
      isProcessingQueueRef.current = false;
      setIsSyncing(false);
    }
  }

  function enqueueFinalSegment(transcript: string) {
    const normalized = normalizeTranscript(transcript);
    if (!normalized) {
      return;
    }

    const queueAlreadyContains = pendingSegmentsRef.current.some(
      (segment) => segment.text === normalized,
    );
    const finalListAlreadyContains = finalSegments.includes(normalized);
    if (queueAlreadyContains || finalListAlreadyContains) {
      return;
    }

    pendingSegmentsRef.current.push({
      id: crypto.randomUUID(),
      text: normalized,
    });
    setFinalSegments((current) => [...current, normalized]);
    setSyncStatus(
      `${pendingSegmentsRef.current.length} finalized segment${pendingSegmentsRef.current.length === 1 ? "" : "s"} waiting to sync.`,
    );
    void flushPendingSegments();
  }

  function getRecognitionInstance(): SpeechRecognitionLike | null {
    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
    if (!Recognition) {
      return null;
    }

    if (recognitionRef.current) {
      return recognitionRef.current;
    }

    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = sessionInfo?.language ?? "en-US";

    recognition.onstart = () => {
      setDictationState("listening");
      setSyncStatus((current) => (current === "Not started." ? "Listening..." : current));
    };

    recognition.onend = () => {
      if (keepListeningRef.current) {
        recognition.start();
        return;
      }

      setDictationState((current) => (current === "stopping" ? "idle" : "paused"));
    };

    recognition.onerror = (event) => {
      if (event.error === "not-allowed") {
        setError("Microphone access was denied.");
      } else if (event.error === "no-speech") {
        setSyncStatus("Listening for speech...");
        return;
      } else {
        setError(`Dictation recognition error${event.error ? `: ${event.error}` : "."}`);
      }
      keepListeningRef.current = false;
      setDictationState("paused");
    };

    recognition.onresult = (event) => {
      let nextPartial = "";

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = normalizeTranscript(
          Array.from(result)
            .map((item) => item.transcript)
            .join(" "),
        );

        if (!transcript) {
          continue;
        }

        if (result.isFinal) {
          enqueueFinalSegment(transcript);
          nextPartial = "";
        } else {
          nextPartial = transcript;
        }
      }

      setPartialTranscript(nextPartial);
    };

    recognitionRef.current = recognition;
    return recognition;
  }

  async function initializeSession() {
    const session = await createDictationSession(encounterId);
    setSessionInfo(session);
    return session;
  }

  async function startDictation() {
    setError(null);
    setDictationState("starting");
    setSyncStatus("Initializing dictation session...");

    try {
      const session = sessionInfo ?? (await initializeSession());

      if (!session.supports_browser_audio) {
        throw new Error("The current dictation session does not support browser audio input.");
      }

      if (!speechRecognitionSupported) {
        throw new Error(
          "Browser speech recognition is not available here. You can still use the manual segment fallback below.",
        );
      }

      await ensureMicrophoneAccess();

      const recognition = getRecognitionInstance();
      if (!recognition) {
        throw new Error(
          "Browser speech recognition is not available here. You can still use the manual segment fallback below.",
        );
      }

      recognition.lang = session.language || "en-US";
      keepListeningRef.current = true;
      recognition.start();
      setSyncStatus("Listening...");
    } catch (error) {
      keepListeningRef.current = false;
      setDictationState("idle");
      const message =
        error instanceof ApiError
          ? error.message
          : error instanceof Error
            ? error.message
            : "Unable to start dictation.";
      setError(message);
      setSyncStatus("Unable to start dictation.");
    }
  }

  function pauseDictation() {
    keepListeningRef.current = false;
    recognitionRef.current?.stop();
    setPartialTranscript("");
    setDictationState("paused");
    setSyncStatus("Dictation paused.");
  }

  async function resumeDictation() {
    if (dictationState !== "paused" && dictationState !== "idle") {
      return;
    }

    if (!speechRecognitionSupported) {
      setError("Browser speech recognition is not available for resume.");
      return;
    }

    setError(null);
    setDictationState("starting");

    try {
      await ensureMicrophoneAccess();
      const recognition = getRecognitionInstance();
      if (!recognition) {
        throw new Error("Browser speech recognition is not available for resume.");
      }

      keepListeningRef.current = true;
      recognition.start();
      setSyncStatus("Listening...");
    } catch (error) {
      keepListeningRef.current = false;
      setDictationState("paused");
      setError(error instanceof Error ? error.message : "Unable to resume dictation.");
    }
  }

  async function stopDictation() {
    setDictationState("stopping");
    keepListeningRef.current = false;
    recognitionRef.current?.stop();
    setPartialTranscript("");
    stopMicrophoneTracks();
    await flushPendingSegments();
    setDictationState("idle");
    setSyncStatus("Dictation stopped.");
  }

  async function submitManualSegment() {
    const normalized = normalizeTranscript(manualSegment);
    if (!normalized) {
      return;
    }

    enqueueFinalSegment(normalized);
    setManualSegment("");
    setPartialTranscript("");
  }

  return (
    <div
      className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm"
      data-testid="dictation-panel"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold text-slate-950">Live dictation</h2>
          <p className="mt-2 text-sm text-slate-600">
            Optional. Use this when you want to speak the transcript instead of typing it. Finalized
            speech is appended to the transcript and can help update the SOAP draft gradually.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button
            variant="secondary"
            onClick={() => void startDictation()}
            disabled={dictationState === "starting" || dictationState === "listening"}
            data-testid="dictation-start-button"
          >
            {dictationState === "starting" ? "Starting..." : "Start"}
          </Button>
          <Button
            variant="secondary"
            onClick={pauseDictation}
            disabled={dictationState !== "listening"}
            data-testid="dictation-pause-button"
          >
            Pause
          </Button>
          <Button
            variant="secondary"
            onClick={() => void resumeDictation()}
            disabled={dictationState !== "paused"}
            data-testid="dictation-resume-button"
          >
            Resume
          </Button>
          <Button
            onClick={() => void stopDictation()}
            disabled={dictationState === "idle"}
            data-testid="dictation-stop-button"
          >
            Stop
          </Button>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-800">Session status</p>
          <p className="mt-2 text-sm text-slate-600">
            {sessionInfo?.message ??
              "Dictation is not connected to a realtime transcription provider yet. You can still test it with the microphone flow or the manual segment box."}
          </p>
          <p className="mt-2 text-xs text-slate-500">
            {sessionInfo
              ? `${sessionInfo.provider} • ${sessionInfo.connection_method} • ${sessionInfo.model}`
              : "Dictation session not initialized yet."}
          </p>
          <p
            className="mt-2 text-xs text-slate-500"
            role="status"
            aria-live="polite"
            data-testid="dictation-status"
          >
            State: {dictationState}. {syncStatus}
          </p>
          {lastSyncedAt ? (
            <p className="mt-2 text-xs text-slate-500">
              Last synced: {new Date(lastSyncedAt).toLocaleTimeString("en-US")}
            </p>
          ) : null}
          {dictationError ? (
            <p
              className="mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
              role="alert"
              data-testid="dictation-error"
            >
              {dictationError}
            </p>
          ) : null}
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <label
            htmlFor="manual-dictation-segment"
            className="block text-sm font-semibold text-slate-800"
          >
            Type a transcript segment instead
          </label>
          <textarea
            id="manual-dictation-segment"
            data-testid="manual-dictation-segment"
            rows={4}
            value={manualSegment}
            onChange={(event) => setManualSegment(event.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900"
            placeholder="Patient denies fever or chills."
          />
          <div className="mt-3 flex flex-wrap gap-3">
            <Button
              variant="secondary"
              onClick={() => void submitManualSegment()}
              disabled={manualSegment.trim().length < 3 || isSyncing}
              data-testid="add-manual-segment-button"
            >
              Add finalized segment
            </Button>
            <Button
              variant="secondary"
              onClick={() => setManualSegment("Follow up in 2 weeks if pain persists.")}
              disabled={isSyncing}
            >
              Try plan segment
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-800">Partial transcript</p>
          <p
            className="mt-2 min-h-16 rounded-md bg-white px-3 py-2 text-sm text-slate-700"
            data-testid="partial-transcript"
            role="status"
            aria-live="polite"
          >
            {partialTranscript || "Waiting for partial transcript updates."}
          </p>
        </div>

        <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-800">Finalized segments</p>
          {finalSegments.length === 0 ? (
            <p className="mt-2 text-sm text-slate-600">
              Final transcript segments will appear here after speech is finalized.
            </p>
          ) : (
            <div className="mt-2 space-y-2" data-testid="finalized-segments">
              {finalSegments.slice(-6).map((segment, index) => (
                <div
                  key={`${segment}-${index}`}
                  className="rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
                >
                  {segment}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
