import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap } from "lucide-react";
import { adminApi, setAdminSession, type AdminMembership } from "../../../infrastructure/adminApi";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [memberships, setMemberships] = useState<AdminMembership[] | null>(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await adminApi.login(email, password);
      const managers = res.memberships.filter((m) => m.role === "owner" || m.role === "manager");
      if (managers.length === 0) {
        setError("Tu usuario no administra ningún comercio.");
        return;
      }
      if (managers.length === 1) {
        setAdminSession(res.access_token, managers[0]);
        navigate("/admin");
        return;
      }
      setToken(res.access_token);
      setMemberships(managers);
    } catch (err) {
      setError(err instanceof Error && err.message === "invalid_credentials"
        ? "Email o contraseña incorrectos."
        : "No se pudo iniciar sesión.");
    } finally {
      setBusy(false);
    }
  };

  const pickTenant = (m: AdminMembership) => {
    setAdminSession(token, m);
    navigate("/admin");
  };

  return (
    <div className="flex min-h-dvh items-center justify-center bg-bg-primary px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex items-center justify-center gap-2">
          <Zap className="text-accent" size={28} />
          <h1 className="text-2xl font-bold">Lightning POS · Admin</h1>
        </div>

        {memberships ? (
          <div className="flex flex-col gap-2">
            <p className="mb-2 text-sm text-text-secondary">Elige el comercio a administrar:</p>
            {memberships.map((m) => (
              <button
                key={m.tenant_id}
                onClick={() => pickTenant(m)}
                className="rounded-lg border border-border-default bg-bg-surface px-4 py-3 text-left hover:border-accent"
              >
                <p className="font-medium">{m.tenant_name}</p>
                <p className="text-xs text-text-secondary">{m.role}</p>
              </button>
            ))}
          </div>
        ) : (
          <form onSubmit={submit} className="flex flex-col gap-3">
            <input
              type="email"
              required
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              data-testid="admin-email"
              className="rounded-lg border border-border-default bg-bg-surface px-4 py-3 outline-none focus:border-accent"
            />
            <input
              type="password"
              required
              placeholder="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              data-testid="admin-password"
              className="rounded-lg border border-border-default bg-bg-surface px-4 py-3 outline-none focus:border-accent"
            />
            {error && (
              <p className="rounded-lg bg-error/10 px-4 py-2 text-sm text-error">{error}</p>
            )}
            <button
              type="submit"
              disabled={busy}
              data-testid="admin-login-submit"
              className="rounded-lg bg-accent px-4 py-3 font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
            >
              {busy ? "Entrando..." : "Entrar"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
