import { useCallback, useEffect, useState } from "react";
import {
  DEMO_TOKEN,
  exitDemo,
  isDemoActive,
  maybeStartDemo,
  tryDemoLogin,
} from "../../infrastructure/demo";

const TOKEN_STORAGE_KEY = "lpos.auth.token";

// Arranca el modo demo (deep-link /demo o flag persistido) ANTES de leer el
// token, para que la sesión use DEMO_TOKEN y el shim de red quede instalado.
const _demoBoot = maybeStartDemo();

function readStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeStoredToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
    else localStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // noop: storage may be unavailable (private mode, disabled cookies)
  }
}

let _token: string | null = _demoBoot ? DEMO_TOKEN : readStoredToken();

export function getToken(): string | null {
  return _token;
}

export function clearSessionAndReload(): void {
  _token = null;
  writeStoredToken(null);
  // exitDemo tambien borra el flag del demo (lpos.demo) y recarga a "/". Sin eso,
  // maybeStartDemo reactiva el demo en el reload y "Salir" nunca libera al usuario.
  // En sesion normal el flag no existe, asi que removeItem es no-op.
  exitDemo();
}

export function useAuth() {
  const [token, setToken] = useState<string | null>(_token);
  const [pinSet, setPinSet] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  const checkStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/auth/status");
      const data = await res.json();
      setPinSet(data.pin_set);
    } catch {
      setPinSet(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const login = async (pin: string): Promise<boolean> => {
    // PIN mágico del demo → sesión local, sin tocar el backend.
    const demoToken = tryDemoLogin(pin);
    if (demoToken) {
      _token = demoToken;
      writeStoredToken(demoToken);
      setToken(demoToken);
      return true;
    }
    const res = await fetch("/api/auth/verify-pin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    _token = data.token;
    writeStoredToken(data.token);
    setToken(data.token);
    return true;
  };

  const setupPin = async (pin: string): Promise<boolean> => {
    const res = await fetch("/api/auth/setup-pin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
    if (!res.ok) return false;
    setPinSet(true);
    return await login(pin);
  };

  const logout = () => {
    // En demo, salir limpio: borrar el flag y recargar para desinstalar el shim.
    if (isDemoActive()) {
      writeStoredToken(null);
      exitDemo();
      return;
    }
    _token = null;
    writeStoredToken(null);
    setToken(null);
  };

  const authenticated = !!token;

  return { authenticated, pinSet, loading, login, setupPin, logout, token };
}
