import { useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Pencil, Plus, ShieldOff } from "lucide-react";
import { useAdminData } from "../../../application/hooks/useAdminData";
import { adminApi, type AdminTerminal, type PairingCode } from "../../../infrastructure/adminApi";

function Countdown({ expiresAt, onExpired }: { expiresAt: string; onExpired: () => void }) {
  const [left, setLeft] = useState(() =>
    Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000))
  );
  useEffect(() => {
    const t = setInterval(() => {
      const s = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
      setLeft(s);
      if (s === 0) {
        clearInterval(t);
        onExpired();
      }
    }, 1000);
    return () => clearInterval(t);
  }, [expiresAt, onExpired]);
  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");
  return (
    <span className={left < 60 ? "text-error" : "text-text-secondary"}>
      expira en {mm}:{ss}
    </span>
  );
}

export default function AdminTerminalsPage() {
  const { data, error, setError, reload, loading } = useAdminData(adminApi.terminals.list);
  const terminals = data ?? [];
  const [pairing, setPairing] = useState<{ name: string; role: "manager" | "cashier" } | null>(null);
  const [code, setCode] = useState<PairingCode | null>(null);
  const [expired, setExpired] = useState(false);
  const [busy, setBusy] = useState(false);

  const createCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pairing) return;
    setBusy(true);
    try {
      setCode(await adminApi.pairingCodes.create(pairing.name.trim(), pairing.role));
      setExpired(false);
    } catch {
      setError("No se pudo generar el código de pairing.");
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (t: AdminTerminal) => {
    if (!confirm(`¿Revocar "${t.name}"? La terminal se desconectará de inmediato.`)) return;
    await adminApi.terminals.revoke(t.id);
    reload();
  };

  const rename = async (t: AdminTerminal) => {
    const name = prompt("Nuevo nombre de la terminal:", t.name)?.trim();
    if (!name || name === t.name) return;
    await adminApi.terminals.rename(t.id, name);
    reload();
  };

  const closePairing = () => {
    setPairing(null);
    setCode(null);
    setExpired(false);
    reload(); // por si la terminal ya se emparejó
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Terminales</h1>
        <button
          onClick={() => setPairing({ name: "", role: "cashier" })}
          data-testid="admin-terminal-new"
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover"
        >
          <Plus size={16} />
          Emparejar terminal
        </button>
      </div>

      {error && <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">{error}</p>}

      {pairing && (
        <div className="mb-4 rounded-lg border border-border-default bg-bg-surface p-4">
          {code ? (
            <div className="flex flex-col items-center gap-3 py-2 text-center">
              <p className="font-medium">Escanea con la app Lightning POS Terminal</p>
              {expired ? (
                <p className="rounded-lg bg-error/10 px-4 py-8 text-sm text-error">
                  El código expiró. Genera uno nuevo.
                </p>
              ) : (
                <div className="rounded-lg bg-white p-3">
                  <QRCodeSVG value={JSON.stringify(code.pairing_payload)} size={200} />
                </div>
              )}
              <p className="text-sm text-text-secondary">
                Código manual: <span className="font-mono text-text-primary">{code.code}</span>
                {" · "}
                {!expired && <Countdown expiresAt={code.expires_at} onExpired={() => setExpired(true)} />}
              </p>
              <div className="flex gap-2">
                {expired && (
                  <button
                    onClick={(e) => void createCode(e as unknown as React.FormEvent)}
                    className="rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover"
                  >
                    Generar otro
                  </button>
                )}
                <button
                  onClick={closePairing}
                  className="rounded-lg border border-border-default px-4 py-2 text-sm text-text-secondary hover:text-text-primary"
                >
                  Listo
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={createCode} className="flex flex-col gap-3">
              <p className="font-medium">Nueva terminal</p>
              <input
                required
                placeholder="Nombre (ej. Caja 1)"
                value={pairing.name}
                onChange={(e) => setPairing({ ...pairing, name: e.target.value })}
                data-testid="admin-pairing-name"
                className="rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
              />
              <select
                value={pairing.role}
                onChange={(e) => setPairing({ ...pairing, role: e.target.value as "manager" | "cashier" })}
                className="w-48 rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
              >
                <option value="cashier">Cajero</option>
                <option value="manager">Manager</option>
              </select>
              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={busy}
                  data-testid="admin-pairing-generate"
                  className="rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
                >
                  Generar QR
                </button>
                <button
                  type="button"
                  onClick={closePairing}
                  className="rounded-lg border border-border-default px-4 py-2 text-sm text-text-secondary hover:text-text-primary"
                >
                  Cancelar
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {loading ? (
        <p className="text-text-secondary">Cargando...</p>
      ) : terminals.length === 0 ? (
        <div className="mt-16 text-center">
          <p className="text-text-secondary">No hay terminales emparejadas.</p>
          <p className="text-sm text-text-secondary">
            Genera un QR de pairing y escanéalo desde la app móvil.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {terminals.map((t) => (
            <div
              key={t.id}
              className={`flex items-center justify-between rounded-lg border border-border-default bg-bg-surface px-4 py-3 ${
                t.status === "revoked" ? "opacity-50" : ""
              }`}
            >
              <div>
                <p className="font-medium">{t.name}</p>
                <p className="text-sm text-text-secondary">
                  {t.role === "manager" ? "Manager" : "Cajero"} ·{" "}
                  {t.status === "active" ? "activa" : "revocada"}
                </p>
              </div>
              {t.status === "active" && (
                <div className="flex gap-1">
                  <button
                    onClick={() => void rename(t)}
                    aria-label={`Renombrar ${t.name}`}
                    className="rounded-lg p-2 text-text-secondary hover:bg-bg-primary hover:text-text-primary"
                  >
                    <Pencil size={16} />
                  </button>
                  <button
                    onClick={() => void revoke(t)}
                    aria-label={`Revocar ${t.name}`}
                    className="flex items-center gap-1.5 rounded-lg border border-border-default px-3 py-1.5 text-sm text-text-secondary hover:border-error hover:text-error"
                  >
                    <ShieldOff size={14} />
                    Revocar
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
