import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useAdminData } from "../../../application/hooks/useAdminData";
import { adminApi, getAdminSession, type AdminMember } from "../../../infrastructure/adminApi";

const ROLE_LABEL: Record<string, string> = {
  owner: "Dueño",
  manager: "Manager",
  cashier: "Cajero",
};

export default function AdminMembersPage() {
  const session = getAdminSession();
  const isOwner = session?.role === "owner";
  const { data, error, setError, reload, loading } = useAdminData(adminApi.members.list);
  const members = data ?? [];
  const [form, setForm] = useState<{ email: string; password: string; name: string; role: "manager" | "cashier" } | null>(null);
  const [busy, setBusy] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setBusy(true);
    try {
      await adminApi.members.add({
        email: form.email.trim(),
        password: form.password,
        name: form.name.trim() || undefined,
        role: form.role,
      });
      setForm(null);
      reload();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setError(
        msg === "already_member"
          ? "Ese usuario ya es miembro del comercio."
          : msg === "requires_owner"
            ? "Solo el dueño puede crear managers."
            : "No se pudo agregar el miembro."
      );
    } finally {
      setBusy(false);
    }
  };

  const remove = async (m: AdminMember) => {
    if (!confirm(`¿Quitar a ${m.email} del comercio?`)) return;
    try {
      await adminApi.members.remove(m.user_id);
      reload();
    } catch {
      setError("No se pudo quitar (el dueño no puede eliminarse).");
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Miembros</h1>
        <button
          onClick={() => setForm({ email: "", password: "", name: "", role: "cashier" })}
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover"
        >
          <Plus size={16} />
          Agregar
        </button>
      </div>

      {error && <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">{error}</p>}

      {form && (
        <form
          onSubmit={save}
          className="mb-4 flex flex-col gap-3 rounded-lg border border-border-default bg-bg-surface p-4"
        >
          <p className="font-medium">Nuevo miembro</p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              required
              type="email"
              placeholder="Email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="flex-1 rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
            />
            <input
              required
              type="password"
              minLength={8}
              placeholder="Contraseña inicial"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="flex-1 rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
            />
          </div>
          <div className="flex gap-3">
            <input
              placeholder="Nombre (opcional)"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="flex-1 rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
            />
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as "manager" | "cashier" })}
              className="w-40 rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
            >
              <option value="cashier">Cajero</option>
              {isOwner && <option value="manager">Manager</option>}
            </select>
          </div>
          <p className="text-xs text-text-secondary">
            Comparte la contraseña inicial por un canal seguro; el miembro puede cambiarla en Ajustes.
          </p>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
            >
              Agregar
            </button>
            <button
              type="button"
              onClick={() => setForm(null)}
              className="rounded-lg border border-border-default px-4 py-2 text-sm text-text-secondary hover:text-text-primary"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-text-secondary">Cargando...</p>
      ) : (
        <div className="flex flex-col gap-2">
          {members.map((m) => (
            <div
              key={m.user_id}
              className="flex items-center justify-between rounded-lg border border-border-default bg-bg-surface px-4 py-3"
            >
              <div>
                <p className="font-medium">{m.name || m.email}</p>
                <p className="text-sm text-text-secondary">
                  {m.email} · {ROLE_LABEL[m.role] ?? m.role}
                </p>
              </div>
              {isOwner && m.role !== "owner" && (
                <button
                  onClick={() => void remove(m)}
                  aria-label={`Quitar ${m.email}`}
                  className="rounded-lg p-2 text-text-secondary hover:bg-bg-primary hover:text-error"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
