// API pública del modo demo (ver state.ts para el contexto general).

import { installDemoBackend } from "./install";
import {
  DEMO_PIN,
  DEMO_TOKEN,
  demoFlagPersisted,
  markActive,
  persistDemoFlag,
} from "./state";

export { DEMO_TOKEN, isDemoActive, exitDemo } from "./state";

function start(): void {
  markActive();
  persistDemoFlag();
  installDemoBackend();
}

/**
 * Arranca el demo si corresponde: deep-link /demo o flag persistido (recarga).
 * Debe llamarse ANTES de que useAuth lea el token. Devuelve true si el demo
 * quedó activo (entonces la sesión usa DEMO_TOKEN).
 */
export function maybeStartDemo(): boolean {
  if (typeof window === "undefined") return false;
  const onDemoPath = window.location.pathname.startsWith("/demo");
  if (!onDemoPath && !demoFlagPersisted()) return false;
  start();
  return true;
}

/**
 * Login por PIN mágico: si el PIN es el del demo, arranca el modo demo y
 * devuelve el token; si no, devuelve null (login normal contra el backend).
 */
export function tryDemoLogin(pin: string): string | null {
  if (pin.trim() !== DEMO_PIN) return null;
  start();
  return DEMO_TOKEN;
}
