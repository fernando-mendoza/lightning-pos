import { useCallback, useEffect, useRef, useState } from "react";
import type { ExchangeRate } from "../../domain/types";

export function useExchangeRate(refreshInterval = 30_000) {
  const [rate, setRate] = useState<ExchangeRate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval>>();

  const fetchRate = useCallback(async () => {
    try {
      const res = await fetch("/api/exchange-rate");
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
    return () => clearInterval(timer.current);
  }, [fetchRate, refreshInterval]);

  return { rate, error };
}
