import { useState } from "react";
import { adminApi, getAdminSession, setAdminSession, clearAdminSession } from "../../../infrastructure/adminApi";

export default function AdminSettingsPage() {
  const session = getAdminSession();
  const isOwner = session?.role === "owner";
  const [tenantName, setTenantName] = useState(session?.tenantName ?? "");
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const renameTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;
    setBusy(true);
    setMsg(null);
    try {
      const t = await adminApi.tenant.rename(tenantName.trim());
      // refresca el nombre en la sesión local
      setAdminSession(session.token, {
        tenant_id: t.id,
        tenant_name: t.name,
        role: session.role,
      });
      setMsg({ kind: "ok", text: "Nombre del comercio actualizado." });
    } catch {
      setMsg({ kind: "error", text: "No se pudo renombrar (solo el dueño puede)." });
    } finally {
      setBusy(false);
    }
  };

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      await adminApi.changePassword(current, next);
      setCurrent("");
      setNext("");
      setMsg({ kind: "ok", text: "Contraseña actualizada. Vuelve a iniciar sesión." });
      setTimeout(() => {
        clearAdminSession();
        window.location.replace("/admin/login");
      }, 1500);
    } catch (err) {
      setMsg({
        kind: "error",
        text:
          err instanceof Error && err.message === "invalid_current_password"
            ? "La contraseña actual no es correcta."
            : "No se pudo cambiar la contraseña.",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex max-w-lg flex-col gap-6">
      <h1 className="text-2xl font-bold">Ajustes</h1>

      {msg && (
        <p
          className={`rounded-lg px-4 py-2 text-sm ${
            msg.kind === "ok" ? "bg-success/10 text-success" : "bg-error/10 text-error"
          }`}
        >
          {msg.text}
        </p>
      )}

      {isOwner && (
        <form
          onSubmit={renameTenant}
          className="flex flex-col gap-3 rounded-lg border border-border-default bg-bg-surface p-4"
        >
          <p className="font-medium">Nombre del comercio</p>
          <input
            required
            maxLength={120}
            value={tenantName}
            onChange={(e) => setTenantName(e.target.value)}
            data-testid="admin-tenant-name"
            className="rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
          />
          <button
            type="submit"
            disabled={busy}
            data-testid="admin-tenant-save"
            className="self-start rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
          >
            Guardar
          </button>
        </form>
      )}

      <form
        onSubmit={changePassword}
        className="flex flex-col gap-3 rounded-lg border border-border-default bg-bg-surface p-4"
      >
        <p className="font-medium">Cambiar contraseña</p>
        <input
          required
          type="password"
          placeholder="Contraseña actual"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          className="rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
        />
        <input
          required
          type="password"
          minLength={8}
          placeholder="Contraseña nueva (mínimo 8 caracteres)"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          className="rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
        />
        <button
          type="submit"
          disabled={busy}
          className="self-start rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
        >
          Cambiar
        </button>
      </form>
    </div>
  );
}
