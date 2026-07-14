export interface WebSocketClientOptions {
  url: string;
  protocols?: string | string[];
  onOpen?: () => void;
  onMessage?: (event: MessageEvent<string>) => void;
  onError?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
}

export function createWebSocketClient(options: WebSocketClientOptions): WebSocket {
  const socket = new WebSocket(options.url, options.protocols);

  if (options.onOpen) {
    socket.addEventListener("open", options.onOpen);
  }

  if (options.onMessage) {
    socket.addEventListener("message", options.onMessage);
  }

  if (options.onError) {
    socket.addEventListener("error", options.onError);
  }

  if (options.onClose) {
    socket.addEventListener("close", options.onClose);
  }

  return socket;
}
