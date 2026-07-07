// Cliente del API multi-tenant /api/v2 para el dashboard del manager.
// Sesión propia (JWT + tenant activo), independiente del PIN del POS v1.

const BASE = "/api/v2";
const TOKEN_KEY = "lpos.admin.token";
const TENANT_KEY = "lpos.admin.tenant";

export interface AdminMembership {
  tenant_id: string;
  tenant_name: string;
  role: string;
}

export interface AdminSession {
  token: string;
  tenantId: string;
  tenantName: string;
  role: string;
}

export function getAdminSession(): AdminSession | null {
  const token = localStorage.getItem(TOKEN_KEY);
  const raw = localStorage.getItem(TENANT_KEY);
  if (!token || !raw) return null;
  try {
    const t = JSON.parse(raw);
    return { token, tenantId: t.id, tenantName: t.name, role: t.role };
  } catch {
    return null;
  }
}

export function setAdminSession(token: string, m: AdminMembership) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(
    TENANT_KEY,
    JSON.stringify({ id: m.tenant_id, name: m.tenant_name, role: m.role })
  );
}

export function clearAdminSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TENANT_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const session = getAdminSession();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (session) {
    headers["Authorization"] = `Bearer ${session.token}`;
    headers["X-Tenant-Id"] = session.tenantId;
  }
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401 && session) {
    clearAdminSession();
    window.location.replace("/admin/login");
    throw new Error("401: sesión expirada");
  }
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json()).detail ?? "";
    } catch {
      /* cuerpo no-JSON */
    }
    throw new Error(detail || `Error ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface AdminProduct {
  id: string;
  name: string;
  price_mxn: string;
  barcode: string | null;
  active: boolean;
}

export interface AdminTerminal {
  id: string;
  name: string;
  role: string;
  status: string;
  created_at: string;
}

export interface PairingCode {
  code: string;
  expires_at: string;
  pairing_payload: { server_url: string; code: string };
}

export interface AdminMember {
  user_id: string;
  email: string;
  name: string | null;
  role: string;
}

export interface ReportRow {
  count: number;
  mxn: string;
  sats: number;
}

export interface ReportSummary {
  from: string;
  to: string;
  totals: ReportRow;
  by_day: (ReportRow & { day: string })[];
  by_terminal: (ReportRow & { terminal_id: string | null; name: string | null })[];
}

export const adminApi = {
  login: (email: string, password: string) =>
    request<{ access_token: string; memberships: AdminMembership[] }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<void>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
  products: {
    list: () => request<AdminProduct[]>("/catalog/manager/products?include_inactive=true"),
    create: (data: { name: string; price_mxn: string; barcode?: string | null }) =>
      request<AdminProduct>("/catalog/products", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: Partial<{ name: string; price_mxn: string; barcode: string | null; active: boolean }>) =>
      request<AdminProduct>(`/catalog/products/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    remove: (id: string) => request<void>(`/catalog/products/${id}`, { method: "DELETE" }),
  },
  terminals: {
    list: () => request<AdminTerminal[]>("/terminals"),
    revoke: (id: string) => request<void>(`/terminals/${id}/revoke`, { method: "POST" }),
    rename: (id: string, name: string) =>
      request<AdminTerminal>(`/terminals/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }),
  },
  pairingCodes: {
    create: (name: string, role: "manager" | "cashier") =>
      request<PairingCode>("/pairing-codes", { method: "POST", body: JSON.stringify({ name, role }) }),
  },
  members: {
    list: () => request<AdminMember[]>("/members"),
    add: (data: { email: string; password?: string; name?: string; role: "manager" | "cashier" }) =>
      request<AdminMember>("/members", { method: "POST", body: JSON.stringify(data) }),
    remove: (userId: string) => request<void>(`/members/${userId}`, { method: "DELETE" }),
  },
  tenant: {
    rename: (name: string) =>
      request<{ id: string; name: string }>("/tenants/me", { method: "PATCH", body: JSON.stringify({ name }) }),
  },
  reports: {
    summary: (from?: string, to?: string) => {
      const q = new URLSearchParams();
      if (from) q.set("from", from);
      if (to) q.set("to", to);
      const qs = q.toString();
      return request<ReportSummary>(`/reports/summary${qs ? `?${qs}` : ""}`);
    },
  },
};
