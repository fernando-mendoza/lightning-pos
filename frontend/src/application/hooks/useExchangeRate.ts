import { useCallback, useEffect, useRef, useState } from "react";
import type { ExchangeRate } from "../../domain/types";
import { getToken, clearSessionAndReload } from "./useAuth";

export function useExchangeRate(refreshInterval = 30_000) {
  const [rate, setRate] = useState<ExchangeRate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRate = useCallback(async () => {
    try {
      const token = getToken();
      const res = await fetch("/api/exchange-rate", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (res.status === 401 && token) {
        clearSessionAndReload();
        return;
      }
      if (!res.ok) throw new Error(`${res.status}`);
      const data: ExchangeRate = await res.json();
      setRate(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error fetching rate");
    }
  }, []);

  useEffect(() => {
    fetchRate();
    timer.current = setInterval(fetchRate, refreshInterval);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [fetchRate, refreshInterval]);

  return { rate, error };
}
