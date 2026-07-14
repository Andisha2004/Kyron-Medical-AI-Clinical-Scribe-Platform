import type { Page } from "@playwright/test";

export async function installSpeechAndMediaMocks(
  page: Page,
  options: { microphone?: "granted" | "denied" } = {},
): Promise<void> {
  const microphone = options.microphone ?? "granted";

  await page.addInitScript(
    ({ microphoneMode }) => {
      type MockRecognitionInstance = {
        onstart: null | (() => void);
        onend: null | (() => void);
        onerror: null | ((event: { error?: string }) => void);
        onresult: null | ((event: { resultIndex: number; results: ArrayLike<unknown> }) => void);
        start: () => void;
        stop: () => void;
        continuous: boolean;
        interimResults: boolean;
        lang: string;
      };

      const instances: MockRecognitionInstance[] = [];
      let microphoneState = microphoneMode;
      let lastSpokenText = "";

      function buildResult(transcript: string, isFinal: boolean) {
        return {
          0: { transcript },
          length: 1,
          isFinal,
        };
      }

      class MockSpeechRecognition {
        continuous = false;
        interimResults = false;
        lang = "en-US";
        onstart: null | (() => void) = null;
        onend: null | (() => void) = null;
        onerror: null | ((event: { error?: string }) => void) = null;
        onresult: null | ((event: { resultIndex: number; results: ArrayLike<unknown> }) => void) =
          null;

        start() {
          instances.push(this);
          this.onstart?.();
        }

        stop() {
          this.onend?.();
        }
      }

      Object.defineProperty(window, "SpeechRecognition", {
        configurable: true,
        writable: true,
        value: MockSpeechRecognition,
      });

      Object.defineProperty(window, "webkitSpeechRecognition", {
        configurable: true,
        writable: true,
        value: MockSpeechRecognition,
      });

      Object.defineProperty(window, "speechSynthesis", {
        configurable: true,
        writable: true,
        value: {
          speak(utterance: SpeechSynthesisUtterance) {
            lastSpokenText = utterance.text;
          },
          cancel() {
            lastSpokenText = "";
          },
        },
      });

      Object.defineProperty(window, "SpeechSynthesisUtterance", {
        configurable: true,
        writable: true,
        value: class {
          text: string;

          constructor(text: string) {
            this.text = text;
          }
        },
      });

      Object.defineProperty(navigator, "mediaDevices", {
        configurable: true,
        value: {
          async getUserMedia() {
            if (microphoneState === "denied") {
              const error = new Error("Microphone access was denied.");
              error.name = "NotAllowedError";
              throw error;
            }

            const track = {
              stop() {},
              addEventListener() {},
            };

            return {
              getTracks: () => [track],
              getAudioTracks: () => [track],
            };
          },
        },
      });

      Object.defineProperty(window, "__mockSpeech", {
        configurable: true,
        writable: true,
        value: {
          setMicrophoneMode(mode: "granted" | "denied") {
            microphoneState = mode;
          },
          emitInterim(transcript: string) {
            const recognition = instances.at(-1);
            recognition?.onresult?.({
              resultIndex: 0,
              results: [buildResult(transcript, false)],
            });
          },
          emitFinal(transcript: string) {
            const recognition = instances.at(-1);
            recognition?.onresult?.({
              resultIndex: 0,
              results: [buildResult(transcript, true)],
            });
          },
          emitError(error: string) {
            const recognition = instances.at(-1);
            recognition?.onerror?.({ error });
          },
          stopLatest() {
            const recognition = instances.at(-1);
            recognition?.stop();
          },
          lastSpokenText() {
            return lastSpokenText;
          },
        },
      });
    },
    { microphoneMode: microphone },
  );
}
