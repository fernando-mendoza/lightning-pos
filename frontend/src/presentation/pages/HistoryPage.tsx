import { useState } from "react";
import { ChevronLeft, ChevronRight, ChevronDown, Download } from "lucide-react";
import { useSales } from "../../application/hooks/useSales";
import type { Sale } from "../../domain/types";

const CSV_HEADERS = [
  "id",
  "created_at",
  "paid_at",
  "status",
  "total_mxn",
  "tip_mxn",
  "discount_mxn",
  "total_sats",
  "exchange_rate",
  "payment_hash",
  "items",
];

function csvEscape(value: string | number | null | undefined): string {
  const str = value === null || value === undefined ? "" : String(value);
  return `"${str.replace(/"/g, '""')}"`;
}

function downloadSalesCsv(sales: Sale[], dateStr: string): void {
  const rows = sales.map((s) => [
    s.id,
    s.created_at,
    s.paid_at ?? "",
    s.status,
    s.total_mxn.toFixed(2),
    s.tip_mxn.toFixed(2),
    s.discount_mxn.toFixed(2),
    s.total_sats,
    s.exchange_rate,
    s.payment_hash,
    s.items.map((i) => `${i.product_name}x${i.quantity}`).join(" | "),
  ]);
  const csv = [CSV_HEADERS, ...rows]
    .map((r) => r.map(csvEscape).join(","))
    .join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ventas-${dateStr}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

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

function formatTimeSeconds(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleTimeString("es-MX", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatDuration(fromIso: string, toIso: string): string {
  const diffMs = new Date(toIso).getTime() - new Date(fromIso).getTime();
  const seconds = Math.max(0, Math.round(diffMs / 1000));
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

function statusMeta(status: Sale["status"]) {
  switch (status) {
    case "paid":
      return { label: "Pagada", dot: "bg-success", text: "text-success" };
    case "expired":
      return { label: "Expirada", dot: "bg-error", text: "text-error" };
    case "canceled":
      return {
        label: "Cancelada",
        dot: "bg-text-secondary",
        text: "text-text-secondary",
      };
    default:
      return { label: "Pendiente", dot: "bg-warning", text: "text-warning" };
  }
}

interface SaleCardProps {
  sale: Sale;
  expanded: boolean;
  onToggle: () => void;
}

function SaleCard({ sale, expanded, onToggle }: SaleCardProps) {
  const [showTechnical, setShowTechnical] = useState(false);
  const meta = statusMeta(sale.status);

  return (
    <div className="rounded-lg border border-border-default bg-bg-surface">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-bg-surface-hover"
        aria-expanded={expanded}
      >
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span
              className={`inline-block h-2 w-2 rounded-full ${meta.dot}`}
              aria-hidden
            />
            <span className="text-xs text-text-secondary">
              {formatTime(sale.created_at)}
            </span>
            <span className={`text-xs font-medium ${meta.text}`}>
              {meta.label}
            </span>
          </div>
          <p className="truncate text-sm text-text-secondary">
            {sale.items
              .map((i) => `${i.product_name} x${i.quantity}`)
              .join(", ")}
          </p>
        </div>

        <div className="flex shrink-0 flex-col items-end">
          <span className="font-mono text-sm font-bold">
            ${sale.total_mxn.toFixed(2)}
          </span>
          <span className="font-mono text-xs text-accent">
            {sale.total_sats.toLocaleString()} sats
          </span>
        </div>

        <ChevronDown
          size={16}
          className={`shrink-0 text-text-secondary transition-transform ${
            expanded ? "rotate-180" : ""
          }`}
        />
      </button>

      {expanded && (
        <div className="space-y-4 border-t border-border-default px-4 py-4">
          {/* Items table */}
          <div>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-text-secondary">
              Items
            </h3>
            <div className="overflow-hidden rounded-md border border-border-default">
              <table className="w-full text-sm">
                <thead className="bg-bg-primary text-xs text-text-secondary">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Producto</th>
                    <th className="px-3 py-2 text-right font-medium">Cant</th>
                    <th className="px-3 py-2 text-right font-medium">P. Unit</th>
                    <th className="px-3 py-2 text-right font-medium">Subtotal</th>
                  </tr>
                </thead>
                <tbody>
                  {sale.items.map((item, idx) => (
                    <tr
                      key={idx}
                      className="border-t border-border-default"
                    >
                      <td className="px-3 py-2">{item.product_name}</td>
                      <td className="px-3 py-2 text-right font-mono">
                        {item.quantity}
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-text-secondary">
                        ${item.price_mxn.toFixed(2)}
                      </td>
                      <td className="px-3 py-2 text-right font-mono">
                        ${item.subtotal_mxn.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Breakdown (solo si hay propina o descuento) */}
          {(sale.tip_mxn > 0 || sale.discount_mxn > 0) && (
            <div>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-text-secondary">
                Desglose
              </h3>
              <dl className="space-y-1 text-sm">
                <div className="flex justify-between">
                  <dt className="text-text-secondary">Subtotal items</dt>
                  <dd className="font-mono">
                    $
                    {(
                      sale.total_mxn - sale.tip_mxn + sale.discount_mxn
                    ).toFixed(2)}
                  </dd>
                </div>
                {sale.discount_mxn > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-text-secondary">Descuento</dt>
                    <dd className="font-mono">-${sale.discount_mxn.toFixed(2)}</dd>
                  </div>
                )}
                {sale.tip_mxn > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-text-secondary">Propina</dt>
                    <dd className="font-mono">+${sale.tip_mxn.toFixed(2)}</dd>
                  </div>
                )}
                <div className="flex justify-between border-t border-border-default pt-1">
                  <dt className="font-medium">Total</dt>
                  <dd className="font-mono font-bold">
                    ${sale.total_mxn.toFixed(2)}
                  </dd>
                </div>
              </dl>
            </div>
          )}

          {/* Metadata grid */}
          <dl className="grid grid-cols-1 gap-y-2 text-sm sm:grid-cols-2 sm:gap-x-6">
            <div className="flex justify-between sm:block">
              <dt className="text-text-secondary">Creada</dt>
              <dd className="font-mono text-right sm:text-left">
                {formatTimeSeconds(sale.created_at)}
              </dd>
            </div>
            {sale.paid_at ? (
              <div className="flex justify-between sm:block">
                <dt className="text-text-secondary">Pagada</dt>
                <dd className="font-mono text-right sm:text-left">
                  {formatTimeSeconds(sale.paid_at)}{" "}
                  <span className="text-xs text-text-secondary">
                    ({formatDuration(sale.created_at, sale.paid_at)})
                  </span>
                </dd>
              </div>
            ) : (
              <div className="flex justify-between sm:block">
                <dt className="text-text-secondary">Pagada</dt>
                <dd className="text-right text-text-secondary sm:text-left">
                  —
                </dd>
              </div>
            )}
            <div className="flex justify-between sm:block">
              <dt className="text-text-secondary">Tipo de cambio</dt>
              <dd className="font-mono text-right sm:text-left">
                {sale.exchange_rate.toLocaleString("es-MX", {
                  maximumFractionDigits: 0,
                })}{" "}
                <span className="text-xs text-text-secondary">MXN/BTC</span>
              </dd>
            </div>
            <div className="flex justify-between sm:block">
              <dt className="text-text-secondary">Total sats</dt>
              <dd className="font-mono text-right text-accent sm:text-left">
                {sale.total_sats.toLocaleString()}
              </dd>
            </div>
          </dl>

          {/* Technical data toggle */}
          <div>
            <button
              onClick={() => setShowTechnical((v) => !v)}
              className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary"
              aria-expanded={showTechnical}
            >
              <ChevronDown
                size={12}
                className={`transition-transform ${
                  showTechnical ? "rotate-0" : "-rotate-90"
                }`}
              />
              Datos tecnicos
            </button>
            {showTechnical && (
              <dl className="mt-2 space-y-1 text-xs">
                <div>
                  <dt className="text-text-secondary">Sale ID</dt>
                  <dd className="break-all font-mono">{sale.id}</dd>
                </div>
                <div>
                  <dt className="text-text-secondary">Payment hash</dt>
                  <dd className="break-all font-mono">{sale.payment_hash}</dd>
                </div>
              </dl>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function HistoryPage() {
  const [date, setDate] = useState(() => new Date());
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const dateStr = formatDate(date);
  const { sales, loading, error, totalMxn, totalSats, count } = useSales(dateStr);

  const isToday = formatDate(date) === formatDate(new Date());

  const prev = () => {
    const d = new Date(date);
    d.setDate(d.getDate() - 1);
    setDate(d);
    setExpandedId(null);
  };

  const next = () => {
    if (isToday) return;
    const d = new Date(date);
    d.setDate(d.getDate() + 1);
    setDate(d);
    setExpandedId(null);
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
          <div className="flex items-center justify-between text-sm">
            <span className="text-text-secondary">
              {count} venta{count !== 1 ? "s" : ""}
            </span>
            <span className="font-mono font-bold">
              ${totalMxn.toFixed(2)} MXN
            </span>
          </div>
          <div className="flex items-center justify-between">
            <button
              onClick={() => downloadSalesCsv(sales, dateStr)}
              className="flex items-center gap-1 text-xs text-text-secondary transition-colors hover:text-accent"
              aria-label="Exportar ventas del dia a CSV"
            >
              <Download size={12} />
              Exportar CSV
            </button>
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
            <SaleCard
              key={sale.id}
              sale={sale}
              expanded={expandedId === sale.id}
              onToggle={() =>
                setExpandedId((curr) => (curr === sale.id ? null : sale.id))
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
