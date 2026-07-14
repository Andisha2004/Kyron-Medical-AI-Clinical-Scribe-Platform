export interface StreamEvent<T> {
  event: string;
  data: T;
}

export function parseServerSentEvent<T>(rawEvent: string): StreamEvent<T> | null {
  const lines = rawEvent.split("\n");
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    event,
    data: JSON.parse(dataLines.join("\n")) as T,
  };
}

export async function streamJsonEvents<T>(
  input: RequestInfo | URL,
  init: RequestInit,
  onEvent: (event: StreamEvent<T>) => void,
): Promise<void> {
  const response = await fetch(input, init);
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Streaming request failed with status ${response.status}.`);
  }

  if (!response.body) {
    throw new Error("Streaming response body is unavailable.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const parsedEvent = parseServerSentEvent<T>(chunk);
      if (parsedEvent) {
        onEvent(parsedEvent);
      }
    }
  }

  const finalChunk = buffer.trim();
  if (finalChunk) {
    const parsedEvent = parseServerSentEvent<T>(finalChunk);
    if (parsedEvent) {
      onEvent(parsedEvent);
    }
  }
}
