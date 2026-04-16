import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useSales } from "../../application/hooks/useSales";

function formatDate(date: Date): string {
  return date.toISOString().split("T")[0];
}

function displayDate(date: Date): string {
  return date.toLocaleDateString("es-MX", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatTime(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

export default function HistoryPage() {
  const [date, setDate] = useState(() => new Date());
  const dateStr = formatDate(date);
  const { sales, loading, error, totalMxn, totalSats, count } = useSales(dateStr);

  const isToday = formatDate(date) === formatDate(new Date());

  const prev = () => {
    const d = new Date(date);
    d.setDate(d.getDate() - 1);
    setDate(d);
  };

  const next = () => {
    if (isToday) return;
    const d = new Date(date);
    d.setDate(d.getDate() + 1);
    setDate(d);
  };

  return (
    <div>
      {/* Date navigation */}
      <div className="mb-4 flex items-center justify-between">
        <button
          onClick={prev}
          className="rounded-lg p-2 text-text-secondary hover:bg-bg-surface-hover hover:text-text-primary"
        >
          <ChevronLeft size={20} />
        </button>
        <h1 className="text-sm font-medium">{displayDate(date)}</h1>
        <button
          onClick={next}
          disabled={isToday}
          className="rounded-lg p-2 text-text-secondary hover:bg-bg-surface-hover hover:text-text-primary disabled:opacity-30"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      {/* Day summary */}
      {!loading && count > 0 && (
        <div className="mb-4 rounded-lg border border-border-default bg-bg-surface px-4 py-3">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">{count} venta{count !== 1 ? "s" : ""}</span>
            <span className="font-mono font-bold">${totalMxn.toFixed(2)} MXN</span>
          </div>
          <div className="flex justify-end">
            <span className="font-mono text-sm text-accent">
              {totalSats.toLocaleString()} sats
            </span>
          </div>
        </div>
      )}

      {/* Content */}
      {error && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-text-secondary">Cargando...</p>
      ) : sales.length === 0 ? (
        <div className="mt-16 text-center">
          <p className="text-text-secondary">Sin ventas este dia.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {sales.map((sale) => (
            <div
              key={sale.id}
              className="rounded-lg border border-border-default bg-bg-surface px-4 py-3"
            >
              <div className="mb-1 flex items-center justify-between">
                <span className="text-xs text-text-secondary">
                  {formatTime(sale.created_at)}
                </span>
                <span className="font-mono text-sm font-bold">
                  ${sale.total_mxn.toFixed(2)}
                </span>
              </div>
              <div className="mb-1 flex items-center justify-between">
                <span className="text-sm text-text-secondary">
                  {sale.items.map((i) => `${i.product_name} x${i.quantity}`).join(", ")}
                </span>
                <span className="font-mono text-xs text-accent">
                  {sale.total_sats.toLocaleString()} sats
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
