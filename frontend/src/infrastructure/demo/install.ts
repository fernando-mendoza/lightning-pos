// Instala los shims del modo demo: intercepta window.fetch (todo /api/*) y
// window.WebSocket (/ws/payments) para que TODA la actividad de red se resuelva
// local, sin tocar el backend. Idempotente.

import { handleApi, onDemoPayment, type DemoPaymentEvent } from "./backend";

let installed = false;

function urlPath(input: RequestInfo | URL): string {
  const raw =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;
  try {
    // rutas relativas ("/api/…") o absolutas: normalizamos a pathname+search
    const u = new URL(raw, window.location.origin);
    return u.pathname + u.search;
  } catch {
    return raw;
  }
}

function jsonResponse(status: number, body: unknown): Response {
  if (status === 204 || body === undefined) {
    return new Response(null, { status });
  }
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function safeParseBody(body: BodyInit | null | undefined): unknown {
  if (typeof body !== "string") return undefined;
  try {
    return JSON.parse(body);
  } catch {
    return undefined;
  }
}

function methodOf(input: RequestInfo | URL, init?: RequestInit): string {
  if (init?.method) return init.method;
  if (typeof input !== "string" && !(input instanceof URL)) return input.method;
  return "GET";
}

/** WebSocket falso que solo entiende /ws/payments: se suscribe al notifier de pagos. */
class DemoSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  readyState = DemoSocket.OPEN;
  onopen: ((ev: unknown) => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: unknown) => void) | null = null;
  onerror: ((ev: unknown) => void) | null = null;

  private unsub: () => void;

  constructor() {
    this.unsub = onDemoPayment((payload: DemoPaymentEvent) => {
      this.onmessage?.({
        data: JSON.stringify({ type: "payment_confirmed", ...payload }),
      });
    });
    setTimeout(() => this.onopen?.({}), 0);
  }

  send(): void {
    /* no-op en demo */
  }

  close(): void {
    this.readyState = DemoSocket.CLOSED;
    this.unsub();
    this.onclose?.({});
  }

  addEventListener(): void {
    /* el código usa on*; no-op */
  }
  removeEventListener(): void {
    /* no-op */
  }
}

export function installDemoBackend(): void {
  if (installed || typeof window === "undefined") return;
  installed = true;

  // --- fetch shim: intercepta /api/*, deja pasar lo demás (assets, etc.) ---
  const origFetch = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const path = urlPath(input);
    if (path.startsWith("/api/")) {
      const method = methodOf(input, init);
      const body =
        init?.body !== undefined
          ? safeParseBody(init.body)
          : undefined;
      const { status, body: resBody } = handleApi(method, path, body);
      return jsonResponse(status, resBody);
    }
    return origFetch(input, init);
  };

  // --- WebSocket shim: solo /ws/payments; el resto usa el original ---
  const OrigWS = window.WebSocket;
  window.WebSocket = new Proxy(OrigWS, {
    construct(target, args: [string | URL, (string | string[])?]) {
      const url = String(args[0]);
      if (url.includes("/ws/payments")) {
        return new DemoSocket() as unknown as WebSocket;
      }
      return Reflect.construct(target, args);
    },
  });
}
