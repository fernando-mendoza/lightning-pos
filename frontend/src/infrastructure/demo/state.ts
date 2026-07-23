// Modo demostración del PoS web.
//
// El demo corre 100% en el navegador — CERO conexión al backend (requisito de
// seguridad): se entra con el PIN mágico 1111 (en el login) o con el deep-link
// /demo (compartible). Mientras está activo, un shim de fetch/WebSocket
// (ver install.ts) atiende todo /api/* y /ws/* con datos mock locales, así que
// ninguna petición sale a producción.

export const DEMO_PIN = "1111";
export const DEMO_TOKEN = "demo-session";

const FLAG_KEY = "lpos.demo";

let active = false;

export function isDemoActive(): boolean {
  return active;
}

export function markActive(): void {
  active = true;
}

export function demoFlagPersisted(): boolean {
  try {
    return localStorage.getItem(FLAG_KEY) === "1";
  } catch {
    return false;
  }
}

export function persistDemoFlag(): void {
  try {
    localStorage.setItem(FLAG_KEY, "1");
  } catch {
    // storage may be unavailable (private mode) — el demo sigue vivo en memoria
  }
}

/** Sale del modo demo: limpia el flag y recarga a "/" para desinstalar el shim. */
export function exitDemo(): void {
  try {
    localStorage.removeItem(FLAG_KEY);
  } catch {
    // noop
  }
  if (typeof window !== "undefined") window.location.replace("/");
}
