type PaymentHandler = (data: { payment_hash: string; sale_id: string }) => void;

let socket: WebSocket | null = null;
let handler: PaymentHandler | null = null;
let reconnectTimer: ReturnType<typeof setTimeout>;

function getWsUrl(): string {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${location.host}/ws/payments`;
}

function connect() {
  if (socket?.readyState === WebSocket.OPEN) return;

  socket = new WebSocket(getWsUrl());

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "payment_confirmed" && handler) {
        handler(data);
      }
    } catch {
      // ignore malformed messages
    }
  };

  socket.onclose = () => {
    clearTimeout(reconnectTimer);
    reconnectTimer = setTimeout(connect, 3000);
  };

  socket.onerror = () => {
    socket?.close();
  };
}

export function subscribePayments(cb: PaymentHandler): () => void {
  handler = cb;
  connect();
  return () => {
    handler = null;
  };
}

export function disconnectWs() {
  clearTimeout(reconnectTimer);
  handler = null;
  socket?.close();
  socket = null;
}
