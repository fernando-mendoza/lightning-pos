import { useEffect, useState } from "react";
import { subscribePayments } from "../../infrastructure/ws";

export function usePaymentStatus(paymentHash: string | null) {
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    if (!paymentHash) return;

    const unsub = subscribePayments((data) => {
      if (data.payment_hash === paymentHash) {
        setConfirmed(true);
      }
    });

    return unsub;
  }, [paymentHash]);

  const reset = () => setConfirmed(false);

  return { confirmed, reset };
}
