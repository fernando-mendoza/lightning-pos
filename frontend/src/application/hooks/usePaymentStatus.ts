import { useEffect, useRef, useState } from "react";
import { subscribePayments } from "../../infrastructure/ws";
import { api } from "../../infrastructure/api";

// Si el WebSocket no confirma el pago dentro de este umbral, arrancamos poll
// por HTTP como fallback. El endpoint GET /invoices/{hash}/status ya existe.
const WS_FALLBACK_TIMEOUT_MS = 8_000;
const POLL_INTERVAL_MS = 2_000;

export function usePaymentStatus(paymentHash: string | null) {
  const [confirmed, setConfirmed] = useState(false);
  const fallbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!paymentHash) return;

    let cancelled = false;

    const stopAll = () => {
      if (fallbackTimerRef.current) {
        clearTimeout(fallbackTimerRef.current);
        fallbackTimerRef.current = null;
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };

    const startPolling = () => {
      if (pollIntervalRef.current || cancelled) return;
      pollIntervalRef.current = setInterval(async () => {
        if (cancelled) return;
        try {
          const data = await api.invoices.status(paymentHash);
          if (!cancelled && data.status === "paid") {
            setConfirmed(true);
            stopAll();
          }
        } catch {
          // reintentar en el siguiente tick
        }
      }, POLL_INTERVAL_MS);
    };

    const unsub = subscribePayments((data) => {
      if (data.payment_hash === paymentHash) {
        setConfirmed(true);
        stopAll();
      }
    });

    fallbackTimerRef.current = setTimeout(startPolling, WS_FALLBACK_TIMEOUT_MS);

    return () => {
      cancelled = true;
      stopAll();
      unsub();
    };
  }, [paymentHash]);

  const reset = () => setConfirmed(false);

  return { confirmed, reset };
}
