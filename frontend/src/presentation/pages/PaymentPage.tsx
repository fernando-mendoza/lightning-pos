import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import QRCode from "react-qr-code";
import { usePaymentStatus } from "../../application/hooks/usePaymentStatus";
import { cart } from "../../application/store/cartStore";

export default function PaymentPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const paymentHash = params.get("hash");
  const bolt11 = params.get("bolt11") ?? "";
  const totalMxn = parseFloat(params.get("mxn") ?? "0");
  const totalSats = parseInt(params.get("sats") ?? "0", 10);
  const expiresAt = parseInt(params.get("expires") ?? "0", 10);
  const saleId = params.get("sale") ?? "";

  const { confirmed } = usePaymentStatus(paymentHash);
  const [secondsLeft, setSecondsLeft] = useState(() => {
    if (!expiresAt) return 300;
    return Math.max(0, expiresAt - Math.floor(Date.now() / 1000));
  });

  // Countdown
  useEffect(() => {
    if (secondsLeft <= 0) return;
    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        const next = expiresAt
          ? Math.max(0, expiresAt - Math.floor(Date.now() / 1000))
          : prev - 1;
        return next;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [expiresAt, secondsLeft]);

  // Redirect on confirmed
  useEffect(() => {
    if (confirmed) {
      cart.clear();
      navigate(
        `/pos/confirmed?mxn=${totalMxn}&sats=${totalSats}&sale=${saleId}`,
        { replace: true }
      );
    }
  }, [confirmed, navigate, totalMxn, totalSats, saleId]);

  if (!paymentHash || !bolt11) {
    navigate("/pos", { replace: true });
    return null;
  }

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const expired = secondsLeft <= 0;

  return (
    <div className="flex min-h-[calc(100dvh-64px)] flex-col items-center justify-center px-4">
      <button
        onClick={() => navigate("/pos")}
        className="mb-6 self-start text-sm text-text-secondary hover:text-text-primary"
      >
        &larr; Cancelar
      </button>

      <p className="mb-1 font-mono text-2xl font-bold">
        ${totalMxn.toFixed(2)} MXN
      </p>
      <p className="mb-6 font-mono text-lg text-accent">
        {totalSats.toLocaleString()} sats
      </p>

      <div className="rounded-xl bg-white p-4">
        <QRCode
          value={bolt11.toUpperCase()}
          size={256}
          level="M"
          style={{ width: "100%", maxWidth: 256, height: "auto" }}
        />
      </div>

      {expired ? (
        <div className="mt-6 space-y-3 text-center">
          <p className="text-error">Invoice expirado</p>
          <button
            onClick={() => navigate("/pos", { replace: true })}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover"
          >
            Generar nuevo
          </button>
          <button
            onClick={() => {
              cart.clear();
              navigate("/pos", { replace: true });
            }}
            className="block mx-auto text-xs text-text-secondary hover:text-text-primary"
          >
            Cancelar venta
          </button>
        </div>
      ) : (
        <div className="mt-6 text-center">
          <div className="flex items-center gap-2 text-warning">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-warning" />
            <span className="text-sm">Esperando pago...</span>
          </div>
          <p className="mt-1 font-mono text-xs text-text-secondary">
            Expira en {minutes}:{seconds.toString().padStart(2, "0")}
          </p>
        </div>
      )}
    </div>
  );
}
