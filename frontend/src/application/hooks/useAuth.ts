import { useCallback, useEffect, useState } from "react";

let _token: string | null = null;

export function getToken(): string | null {
  return _token;
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
    const res = await fetch("/api/auth/verify-pin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    _token = data.token;
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
    _token = null;
    setToken(null);
  };

  const authenticated = !!token;

  return { authenticated, pinSet, loading, login, setupPin, logout, token };
}
