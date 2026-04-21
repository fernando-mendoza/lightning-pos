import { test, expect, request as apiRequest } from "@playwright/test";

// E2E del escenario 1 del ICM de concurrencia — poll fallback cuando el WS no entrega.
//
// El test:
//   1. Hace setup del PIN y login via API.
//   2. Crea un invoice real (test mode usa FakeLightningService).
//   3. Abre la pagina de pago con un stub de WebSocket que nunca dispara eventos.
//   4. POSTea el webhook de LNbits.
//   5. Asserts que la pagina navega a /pos/confirmed dentro de 15s — el unico camino
//      posible es el poll fallback (WS_FALLBACK_TIMEOUT_MS=8s + POLL_INTERVAL_MS=2s).

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";
const TEST_PIN = "1234";

async function getToken() {
  const api = await apiRequest.newContext({ baseURL: BACKEND_URL });
  // Idempotente: si el PIN ya esta seteado de un test anterior, responde 409.
  await api.post("/api/auth/setup-pin", { data: { pin: TEST_PIN } });
  const loginResp = await api.post("/api/auth/verify-pin", {
    data: { pin: TEST_PIN },
  });
  expect(loginResp.ok()).toBeTruthy();
  const { token } = await loginResp.json();
  return { api, token };
}

test("poll fallback detecta el pago cuando el WS no entrega", async ({ page }) => {
  const { api, token } = await getToken();

  const invoiceResp = await api.post("/api/invoices", {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      items: [
        { product_id: "p1", product_name: "Cafe", price_mxn: 50.0, quantity: 1 },
      ],
    },
  });
  expect(invoiceResp.status()).toBe(201);
  const invoice = await invoiceResp.json();

  // Pre-inject: token en localStorage + stub de WebSocket que nunca dispara mensajes.
  // El stub corre antes de que cargue el JS de la app, asi que `new WebSocket(...)`
  // dentro de ws.ts recibe esta clase falsa.
  await page.addInitScript(({ token }) => {
    localStorage.setItem("lpos.auth.token", token);
    (window as unknown as { WebSocket: unknown }).WebSocket = class StubWS {
      readyState = 0;
      onopen: ((this: unknown, ev: unknown) => unknown) | null = null;
      onmessage: ((this: unknown, ev: unknown) => unknown) | null = null;
      onclose: ((this: unknown, ev: unknown) => unknown) | null = null;
      onerror: ((this: unknown, ev: unknown) => unknown) | null = null;
      constructor(public url: string) {}
      close() {}
      send() {}
      addEventListener() {}
      removeEventListener() {}
    };
  }, { token });

  const params = new URLSearchParams({
    hash: invoice.payment_hash,
    bolt11: invoice.bolt11,
    mxn: String(invoice.total_mxn),
    sats: String(invoice.total_sats),
    expires: String(invoice.expires_at),
    sale: invoice.sale_id,
  });

  await page.goto(`/pos/pay?${params.toString()}`);
  await expect(page.getByText("Esperando pago...")).toBeVisible();

  // LNbits "confirmo" el pago. Como el WS esta stubbeado, la unica manera de que
  // la UI lo detecte es el poll fallback (arranca a los 8s del timer).
  const webhookResp = await api.post("/api/webhooks/lnbits", {
    data: { payment_hash: invoice.payment_hash },
  });
  expect(webhookResp.ok()).toBeTruthy();

  // 8s del timer + hasta 2s del primer tick de poll ~= 10s. 20s de margen.
  await expect(page).toHaveURL(/\/pos\/confirmed/, { timeout: 20_000 });

  await api.dispose();
});
