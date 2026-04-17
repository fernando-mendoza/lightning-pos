import { getToken, clearSessionAndReload } from "../application/hooks/useAuth";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...Object.fromEntries(
      Object.entries(init?.headers ?? {}).filter(([, v]) => v != null) as [string, string][]
    ),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401 && token) {
    clearSessionAndReload();
    throw new Error("401: session expired");
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  products: {
    list: () => request<Product[]>("/products"),
    create: (data: ProductInput) =>
      request<Product>("/products", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    update: (id: string, data: ProductInput) =>
      request<Product>(`/products/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    remove: (id: string) =>
      request<void>(`/products/${id}`, { method: "DELETE" }),
  },
  invoices: {
    create: (items: InvoiceItem[]) =>
      request<InvoiceResponse>("/invoices", {
        method: "POST",
        body: JSON.stringify({ items }),
      }),
    status: (paymentHash: string) =>
      request<{ payment_hash: string; status: string }>(
        `/invoices/${paymentHash}/status`
      ),
  },
};

interface Product {
  id: string;
  name: string;
  price_mxn: number;
  active: boolean;
  created_at: string;
  updated_at: string;
}

interface ProductInput {
  name: string;
  price_mxn: number;
}

interface InvoiceItem {
  product_id: string;
  product_name: string;
  price_mxn: number;
  quantity: number;
}

interface InvoiceResponse {
  sale_id: string;
  payment_hash: string;
  bolt11: string;
  total_mxn: number;
  total_sats: number;
  exchange_rate: number;
  expires_at: number;
}
