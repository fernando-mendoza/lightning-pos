import { useCallback, useState } from "react";
import { useAdminData } from "../../../application/hooks/useAdminData";
import { adminApi } from "../../../infrastructure/adminApi";

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  return d.toISOString().slice(0, 10);
}

const RANGES = [
  { key: "7d", label: "7 días", days: 6 },
  { key: "30d", label: "30 días", days: 29 },
  { key: "90d", label: "90 días", days: 89 },
] as const;

const mxn = (v: string | number) =>
  `$${Number(v).toLocaleString("es-MX", { minimumFractionDigits: 2 })}`;

/** Desglose efectivo/Lightning de una fila. Se omite si todo entró por un solo método:
 *  repetir "$500 · $500 efectivo · $0 Lightning" no informa, sólo hace ruido. */
function MethodSplit({ cash, lightning }: { cash: string; lightning: string }) {
  const c = Number(cash);
  const l = Number(lightning);
  if (c === 0 || l === 0) return null;
  return (
    <span className="text-text-secondary">
      {" "}
      ({mxn(c)} efectivo · {mxn(l)} Lightning)
    </span>
  );
}

export default function AdminReportsPage() {
  const [range, setRange] = useState<(typeof RANGES)[number]>(RANGES[1]);
  const fetcher = useCallback(
    () => adminApi.reports.summary(isoDaysAgo(range.days), isoDaysAgo(0)),
    [range]
  );
  const { data, error } = useAdminData(fetcher);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Reportes</h1>
        <div className="flex gap-1">
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r)}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                range.key === r.key
                  ? "bg-accent font-bold text-bg-primary"
                  : "border border-border-default text-text-secondary hover:text-text-primary"
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">{error}</p>}

      {!data ? (
        <p className="text-text-secondary">Cargando...</p>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-border-default bg-bg-surface p-4">
              <p className="text-sm text-text-secondary">Ventas cobradas</p>
              <p className="text-2xl font-bold" data-testid="report-count">{data.totals.count}</p>
              <p className="mt-1 text-xs text-text-secondary" data-testid="report-count-split">
                {data.totals.cash_count} efectivo · {data.totals.lightning_count} Lightning
              </p>
            </div>
            <div className="rounded-lg border border-border-default bg-bg-surface p-4">
              <p className="text-sm text-text-secondary">Total cobrado</p>
              <p className="text-2xl font-bold" data-testid="report-total-mxn">{mxn(data.totals.mxn)}</p>
              <p className="mt-1 text-xs text-text-secondary" data-testid="report-mxn-split">
                {mxn(data.totals.cash_mxn)} efectivo · {mxn(data.totals.lightning_mxn)} Lightning
              </p>
            </div>
            {/* Los sats son un SUBCONJUNTO del total, no otra magnitud al mismo nivel: una
                venta en efectivo suma pesos y cero sats. El rótulo lo dice explícitamente
                para que nadie lea "total" dos veces y crea que son ingresos distintos. */}
            <div className="rounded-lg border border-border-default bg-bg-surface p-4">
              <p className="text-sm text-text-secondary">Recibido en Lightning</p>
              <p className="text-2xl font-bold text-accent">{data.totals.sats.toLocaleString()}</p>
              <p className="mt-1 text-xs text-text-secondary">
                sats · parte del total, no adicional
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <section>
              <h2 className="mb-2 font-medium">Por día</h2>
              {data.by_day.length === 0 ? (
                <p className="text-sm text-text-secondary">Sin ventas en el rango.</p>
              ) : (
                <div className="flex flex-col gap-1">
                  {data.by_day.map((d) => (
                    <div
                      key={d.day}
                      className="flex items-center justify-between rounded-lg border border-border-default bg-bg-surface px-3 py-2 text-sm"
                    >
                      <span className="text-text-secondary">{d.day}</span>
                      <span className="text-right">
                        {d.count} venta{d.count === 1 ? "" : "s"} · {mxn(d.mxn)}
                        <MethodSplit cash={d.cash_mxn} lightning={d.lightning_mxn} />
                        {d.sats > 0 && (
                          <span className="text-accent"> · {d.sats.toLocaleString()} sats</span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section>
              <h2 className="mb-2 font-medium">Por terminal</h2>
              {data.by_terminal.length === 0 ? (
                <p className="text-sm text-text-secondary">Sin ventas en el rango.</p>
              ) : (
                <div className="flex flex-col gap-1">
                  {data.by_terminal.map((t) => (
                    <div
                      key={t.terminal_id ?? "none"}
                      className="flex items-center justify-between rounded-lg border border-border-default bg-bg-surface px-3 py-2 text-sm"
                    >
                      <span>{t.name ?? "Sin terminal"}</span>
                      <span className="text-right">
                        {t.count} venta{t.count === 1 ? "" : "s"} · {mxn(t.mxn)}
                        <MethodSplit cash={t.cash_mxn} lightning={t.lightning_mxn} />
                        {t.sats > 0 && (
                          <span className="text-accent"> · {t.sats.toLocaleString()} sats</span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
