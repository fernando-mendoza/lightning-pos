import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Check } from "lucide-react";

export default function ConfirmationPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const totalMxn = parseFloat(params.get("mxn") ?? "0");
  const totalSats = parseInt(params.get("sats") ?? "0", 10);

  // Auto-redirect after 10 seconds
  useEffect(() => {
    const timer = setTimeout(() => navigate("/pos", { replace: true }), 10_000);
    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="flex min-h-[calc(100dvh-64px)] flex-col items-center justify-center px-4">
      <div className="mb-4 flex h-20 w-20 items-center justify-center rounded-full bg-success/20 animate-[scale-in_0.3s_ease-out]">
        <Check size={40} className="text-success" />
      </div>

      <h1 className="mb-2 text-2xl font-bold">Pagado</h1>

      <p className="mb-1 font-mono text-xl font-bold">
        ${totalMxn.toFixed(2)} MXN
      </p>
      <p className="mb-2 font-mono text-accent">
        {totalSats.toLocaleString()} sats
      </p>

      <p className="mb-8 text-xs text-text-secondary">
        {new Date().toLocaleString("es-MX", {
          hour: "2-digit",
          minute: "2-digit",
          day: "numeric",
          month: "short",
          year: "numeric",
        })}
      </p>

      <button
        onClick={() => navigate("/pos", { replace: true })}
        className="rounded-lg bg-accent px-8 py-3 font-bold text-bg-primary hover:bg-accent-hover"
      >
        Nueva venta
      </button>
    </div>
  );
}
