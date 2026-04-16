const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
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
