import { useDashboard } from "../../application/hooks/useDashboard";
import type { DailyEntry } from "../../application/hooks/useDashboard";
import BrandingFooter from "../components/BrandingFooter";

function shortDayLabel(isoDate: string): string {
  const d = new Date(isoDate + "T00:00:00");
  return d.toLocaleDateString("es-MX", { weekday: "narrow" });
}

function dayNumber(isoDate: string): string {
  const d = new Date(isoDate + "T00:00:00");
  return String(d.getDate());
}

function formatMxn(n: number): string {
  return `$${n.toFixed(2)}`;
}

interface BarChartProps {
  data: DailyEntry[];
}

function SalesBarChart({ data }: BarChartProps) {
  const max = Math.max(1, ...data.map((d) => d.total_mxn));
  const todayIso = new Date().toISOString().slice(0, 10);

  // Columnas fluidas (flex-1) en vez de SVG de ancho fijo: el chart ocupa el
  // ancho disponible en cualquier viewport sin encogerse ni distorsionar texto.
  return (
    <div role="img" aria-label="Ventas por dia, ultimos 7 dias">
      <div className="flex h-32 items-end gap-2 sm:gap-4">
        {data.map((d) => {
          const isToday = d.date === todayIso;
          const isEmpty = d.total_mxn === 0;
          const heightPct = isEmpty ? 0 : (d.total_mxn / max) * 100;
          return (
            <div
              key={d.date}
              className="flex h-full flex-1 items-end justify-center"
              title={`${d.date}: ${formatMxn(d.total_mxn)}`}
            >
              <div
                className={`w-full max-w-10 rounded-t-sm ${
                  isEmpty
                    ? "bg-border-default"
                    : isToday
                      ? "bg-accent"
                      : "bg-success"
                }`}
                style={{ height: isEmpty ? "2px" : `${heightPct}%`, minHeight: "2px" }}
              />
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex gap-2 sm:gap-4">
        {data.map((d) => {
          const isToday = d.date === todayIso;
          return (
            <div key={d.date} className="flex-1 text-center">
              <p className="text-[10px] uppercase text-text-secondary">
                {shortDayLabel(d.date)}
              </p>
              <p
                className={`text-[10px] ${
                  isToday ? "text-accent" : "text-text-secondary"
                }`}
              >
                {dayNumber(d.date)}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data, loading, error } = useDashboard();

  if (loading) {
    return <p className="text-text-secondary">Cargando...</p>;
  }

  if (error || !data) {
    return (
      <div className="rounded-lg bg-error/10 px-4 py-3 text-sm text-error">
        {error ?? "Sin datos"}
      </div>
    );
  }

  const weekTotalMxn = data.last_7_days.reduce(
    (s, d) => s + d.total_mxn,
    0
  );
  const weekTotalSats = data.last_7_days.reduce(
    (s, d) => s + d.total_sats,
    0
  );

  return (
    <div className="space-y-6">
      <h1 className="text-lg font-bold">Dashboard</h1>

      {/* Today stats */}
      <section>
        <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-text-secondary">
          Hoy
        </h2>
        <div className="grid grid-cols-3 gap-2">
          <StatCard label="Ventas" value={String(data.today.count)} />
          <StatCard label="MXN" value={formatMxn(data.today.total_mxn)} accent />
          <StatCard
            label="Sats"
            value={data.today.total_sats.toLocaleString()}
          />
        </div>
      </section>

      {/* 7-day chart */}
      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wide text-text-secondary">
            Ultimos 7 dias
          </h2>
          <span className="font-mono text-xs text-text-secondary">
            {formatMxn(weekTotalMxn)} ·{" "}
            <span className="text-accent">
              {weekTotalSats.toLocaleString()} sats
            </span>
          </span>
        </div>
        <div className="rounded-lg border border-border-default bg-bg-surface p-4">
          <SalesBarChart data={data.last_7_days} />
        </div>
      </section>

      {/* Top products */}
      <section>
        <h2 className="mb-2 text-xs font-bold uppercase tracking-wide text-text-secondary">
          Top productos (7 dias)
        </h2>
        {data.top_products.length === 0 ? (
          <p className="text-sm text-text-secondary">
            Sin ventas registradas.
          </p>
        ) : (
          <ol className="flex flex-col gap-2">
            {data.top_products.map((p, i) => (
              <li
                key={p.name}
                className="flex items-center gap-3 rounded-lg border border-border-default bg-bg-surface px-4 py-3"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-bg-primary text-xs font-bold text-accent">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{p.name}</p>
                  <p className="text-xs text-text-secondary">
                    {p.quantity} unidades
                  </p>
                </div>
                <span className="font-mono text-sm">
                  {formatMxn(p.total_mxn)}
                </span>
              </li>
            ))}
          </ol>
        )}
      </section>

      <BrandingFooter />
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: string;
  accent?: boolean;
}

function StatCard({ label, value, accent }: StatCardProps) {
  return (
    <div className="rounded-lg border border-border-default bg-bg-surface px-3 py-3 text-center">
      <p className="text-xs text-text-secondary">{label}</p>
      <p
        className={`font-mono text-base font-bold ${
          accent ? "text-accent" : ""
        }`}
      >
        {value}
      </p>
    </div>
  );
}
