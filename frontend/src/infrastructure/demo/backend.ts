// Backend mock in-memory del modo demo. Atiende todos los endpoints v1 que el
// front consume (auth, products CRUD, invoices, sales, dashboard, exchange-rate)
// con estado en memoria; las invoices se auto-pagan a los ~6 s emitiendo el
// evento de pago (ver payment notifier abajo → lo consume el WebSocket shim).
//
// Formas de respuesta = las de domain/types.ts y infrastructure/api.ts. Nada de
// esto toca la red.

import type { Product, Sale, SaleItem } from "../../domain/types";

// ---------- config ----------
const MXN_PER_BTC = 2_150_000; // tipo de cambio fijo del demo
const SATS_PER_MXN = 100_000_000 / MXN_PER_BTC;
const AUTO_PAY_MS = 6_000; // la invoice demo se confirma a los ~6 s
const INVOICE_TTL_S = 120; // expira en 2 min (expires_at va en segundos unix)

function mxnToSats(mxn: number): number {
  return Math.round(mxn * SATS_PER_MXN);
}

let seq = 0;
function id(prefix: string): string {
  seq += 1;
  return `demo-${prefix}-${seq}`;
}

function isoDaysAgo(days: number, hour = 12): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  d.setHours(hour, 0, 0, 0);
  return d.toISOString();
}

function fakeBolt11(sats: number): string {
  // Prefijo "lnbcfake" = invoice deliberadamente NO pagable; padded para que el
  // QR se vea como un bolt11 real.
  const pad = "qpzry9x8gf2tvdw0s3jn54khce6mua7l".repeat(6);
  return `lnbcfake${sats}n1${pad}`;
}

// ---------- estado ----------
const products: Product[] = [];
const sales: Sale[] = [];
let seeded = false;

function seedProducts(): void {
  const base: [string, number][] = [
    ["Café americano", 45],
    ["Cappuccino", 65],
    ["Latte", 68],
    ["Croissant", 52],
    ["Concha", 28],
    ["Agua mineral", 30],
    ["Playera Lightning", 350],
  ];
  const created = isoDaysAgo(20);
  for (const [name, price] of base) {
    products.push({
      id: id("prod"),
      name,
      price_mxn: price,
      active: true,
      created_at: created,
      updated_at: created,
    });
  }
}

function makeSale(
  items: { product_name: string; price_mxn: number; quantity: number }[],
  status: Sale["status"],
  createdAt: string,
  tipMxn = 0,
  discountMxn = 0,
): Sale {
  const saleId = id("sale");
  const saleItems: SaleItem[] = items.map((i) => ({
    id: id("item"),
    sale_id: saleId,
    product_id: id("pref"),
    product_name: i.product_name,
    price_mxn: i.price_mxn,
    quantity: i.quantity,
    subtotal_mxn: i.price_mxn * i.quantity,
  }));
  const subtotal = saleItems.reduce((s, i) => s + i.subtotal_mxn, 0);
  const total = subtotal + tipMxn - discountMxn;
  const hash = id("hash");
  return {
    id: saleId,
    total_mxn: total,
    total_sats: mxnToSats(total),
    exchange_rate: MXN_PER_BTC,
    payment_hash: hash,
    bolt11: fakeBolt11(mxnToSats(total)),
    status,
    created_at: createdAt,
    paid_at: status === "paid" ? createdAt : null,
    tip_mxn: tipMxn,
    discount_mxn: discountMxn,
    items: saleItems,
  };
}

function seedSales(): void {
  // Historial repartido en los últimos 7 días para poblar dashboard e historial.
  const plan: { day: number; hour: number; items: [string, number, number][]; status?: Sale["status"] }[] = [
    { day: 0, hour: 9, items: [["Café americano", 45, 1], ["Croissant", 52, 1]] },
    { day: 0, hour: 11, items: [["Latte", 68, 2]] },
    { day: 0, hour: 13, items: [["Cappuccino", 65, 1], ["Concha", 28, 1]] },
    { day: 0, hour: 14, items: [["Agua mineral", 30, 1]], status: "expired" },
    { day: 1, hour: 10, items: [["Playera Lightning", 350, 1]] },
    { day: 1, hour: 17, items: [["Café americano", 45, 3]] },
    { day: 2, hour: 12, items: [["Latte", 68, 1], ["Croissant", 52, 2]] },
    { day: 3, hour: 16, items: [["Cappuccino", 65, 2]] },
    { day: 4, hour: 9, items: [["Café americano", 45, 1]] },
    { day: 5, hour: 15, items: [["Concha", 28, 4], ["Agua mineral", 30, 2]] },
    { day: 6, hour: 11, items: [["Latte", 68, 1]] },
  ];
  for (const p of plan) {
    sales.push(
      makeSale(
        p.items.map(([product_name, price_mxn, quantity]) => ({ product_name, price_mxn, quantity })),
        p.status ?? "paid",
        isoDaysAgo(p.day, p.hour),
      ),
    );
  }
}

function ensureSeeded(): void {
  if (seeded) return;
  seeded = true;
  seedProducts();
  seedSales();
}

// ---------- payment notifier (lo consume el WebSocket shim) ----------
export interface DemoPaymentEvent {
  payment_hash: string;
  sale_id: string;
}
type PaymentListener = (e: DemoPaymentEvent) => void;
const paymentListeners = new Set<PaymentListener>();

export function onDemoPayment(cb: PaymentListener): () => void {
  paymentListeners.add(cb);
  return () => paymentListeners.delete(cb);
}

function emitPayment(sale: Sale): void {
  const ev = { payment_hash: sale.payment_hash, sale_id: sale.id };
  paymentListeners.forEach((cb) => cb(ev));
}

function scheduleAutoPay(sale: Sale): void {
  setTimeout(() => {
    if (sale.status === "pending") {
      sale.status = "paid";
      sale.paid_at = new Date().toISOString();
      emitPayment(sale);
    }
  }, AUTO_PAY_MS);
}

// ---------- router ----------
export interface DemoResponse {
  status: number;
  body: unknown;
}

const today = (): string => new Date().toISOString().slice(0, 10);

function parsePath(path: string): { segs: string[]; query: URLSearchParams } {
  const [p, q] = path.split("?");
  return { segs: p.split("/").filter(Boolean), query: new URLSearchParams(q ?? "") };
}

export function handleApi(method: string, path: string, body?: unknown): DemoResponse {
  ensureSeeded();
  const { segs, query } = parsePath(path);
  // segs[0] === "api"
  const m = method.toUpperCase();
  const b = (body ?? {}) as Record<string, unknown>;

  // /api/auth/*
  if (segs[1] === "auth") {
    if (segs[2] === "status") return { status: 200, body: { pin_set: true } };
    if (segs[2] === "verify-pin") return { status: 200, body: { token: "demo-session" } };
    if (segs[2] === "setup-pin") return { status: 200, body: { token: "demo-session" } };
    if (segs[2] === "change-pin") return { status: 200, body: { ok: true } };
  }

  // /api/exchange-rate
  if (segs[1] === "exchange-rate" && m === "GET") {
    return {
      status: 200,
      body: {
        mxn_per_btc: MXN_PER_BTC,
        sats_per_mxn: SATS_PER_MXN,
        fetched_at: Math.floor(Date.now() / 1000),
        source: "Demo",
      },
    };
  }

  // /api/products
  if (segs[1] === "products" && segs.length === 2) {
    if (m === "GET") return { status: 200, body: products.filter((p) => p.active) };
    if (m === "POST") {
      const nowIso = new Date().toISOString();
      const p: Product = {
        id: id("prod"),
        name: String(b.name ?? "Producto"),
        price_mxn: Number(b.price_mxn ?? 0),
        active: true,
        created_at: nowIso,
        updated_at: nowIso,
      };
      products.push(p);
      return { status: 200, body: p };
    }
  }
  if (segs[1] === "products" && segs.length === 3) {
    const p = products.find((x) => x.id === segs[2]);
    if (!p) return { status: 404, body: { detail: "not found" } };
    if (m === "PUT") {
      p.name = String(b.name ?? p.name);
      p.price_mxn = Number(b.price_mxn ?? p.price_mxn);
      p.updated_at = new Date().toISOString();
      return { status: 200, body: p };
    }
    if (m === "DELETE") {
      p.active = false;
      return { status: 204, body: undefined };
    }
  }

  // /api/invoices
  if (segs[1] === "invoices" && segs.length === 2 && m === "POST") {
    const items = (b.items as { product_name: string; price_mxn: number; quantity: number }[]) ?? [];
    const tip = Number(b.tip_mxn ?? 0);
    const discount = Number(b.discount_mxn ?? 0);
    const sale = makeSale(items, "pending", new Date().toISOString(), tip, discount);
    sales.unshift(sale);
    scheduleAutoPay(sale);
    return {
      status: 200,
      body: {
        sale_id: sale.id,
        payment_hash: sale.payment_hash,
        bolt11: sale.bolt11,
        total_mxn: sale.total_mxn,
        total_sats: sale.total_sats,
        exchange_rate: sale.exchange_rate,
        expires_at: Math.floor(Date.now() / 1000) + INVOICE_TTL_S,
        tip_mxn: sale.tip_mxn,
        discount_mxn: sale.discount_mxn,
      },
    };
  }
  if (segs[1] === "invoices" && segs.length === 4) {
    // /api/invoices/{hash}/status  |  /api/invoices/{hash}/cancel
    const hash = segs[2];
    const action = segs[3];
    const sale = sales.find((s) => s.payment_hash === hash);
    if (!sale) return { status: 404, body: { detail: "not found" } };
    if (action === "status") return { status: 200, body: { payment_hash: hash, status: sale.status } };
    if (action === "cancel") {
      if (sale.status === "pending") sale.status = "canceled";
      return { status: 200, body: { payment_hash: hash, status: sale.status } };
    }
  }

  // /api/sales?date=YYYY-MM-DD
  if (segs[1] === "sales" && m === "GET") {
    const date = query.get("date") ?? today();
    const list = sales.filter((s) => s.created_at.slice(0, 10) === date);
    return { status: 200, body: list };
  }

  // /api/dashboard/summary
  if (segs[1] === "dashboard" && segs[2] === "summary" && m === "GET") {
    return { status: 200, body: buildDashboard() };
  }

  // Cualquier /api/* no manejado: 404 local (NUNCA pasa al backend).
  return { status: 404, body: { detail: `demo: unhandled ${m} /${segs.join("/")}` } };
}

function buildDashboard() {
  const paid = sales.filter((s) => s.status === "paid");
  const todayStr = today();

  const todaySales = paid.filter((s) => s.created_at.slice(0, 10) === todayStr);
  const daySummary = {
    total_mxn: todaySales.reduce((a, s) => a + s.total_mxn, 0),
    total_sats: todaySales.reduce((a, s) => a + s.total_sats, 0),
    count: todaySales.length,
  };

  const last7: { date: string; total_mxn: number; total_sats: number; count: number }[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const day = paid.filter((s) => s.created_at.slice(0, 10) === key);
    last7.push({
      date: key,
      total_mxn: day.reduce((a, s) => a + s.total_mxn, 0),
      total_sats: day.reduce((a, s) => a + s.total_sats, 0),
      count: day.length,
    });
  }

  const byProduct = new Map<string, { quantity: number; total_mxn: number }>();
  for (const s of paid) {
    for (const it of s.items) {
      const cur = byProduct.get(it.product_name) ?? { quantity: 0, total_mxn: 0 };
      cur.quantity += it.quantity;
      cur.total_mxn += it.subtotal_mxn;
      byProduct.set(it.product_name, cur);
    }
  }
  const top_products = [...byProduct.entries()]
    .map(([name, v]) => ({ name, quantity: v.quantity, total_mxn: v.total_mxn }))
    .sort((a, b) => b.quantity - a.quantity)
    .slice(0, 5);

  return { today: daySummary, last_7_days: last7, top_products };
}
