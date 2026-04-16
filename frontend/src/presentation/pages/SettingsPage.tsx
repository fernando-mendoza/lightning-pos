import { useState } from "react";
import { useAuth } from "../../application/hooks/useAuth";
import { Lock, LogOut } from "lucide-react";

export default function SettingsPage() {
  const { logout, token } = useAuth();
  const [changingPin, setChangingPin] = useState(false);
  const [currentPin, setCurrentPin] = useState("");
  const [newPin, setNewPin] = useState("");
  const [pinMsg, setPinMsg] = useState<{ type: "ok" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  const handleChangePin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (currentPin.length < 4 || newPin.length < 4) {
      setPinMsg({ type: "error", text: "El PIN debe tener al menos 4 digitos" });
      return;
    }
    setSaving(true);
    setPinMsg(null);
    try {
      const res = await fetch("/api/auth/change-pin", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ current_pin: currentPin, new_pin: newPin }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Error al cambiar PIN");
      }
      setPinMsg({ type: "ok", text: "PIN actualizado" });
      setChangingPin(false);
      setCurrentPin("");
      setNewPin("");
    } catch (e) {
      setPinMsg({ type: "error", text: e instanceof Error ? e.message : "Error" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Configuracion</h1>

      {/* Change PIN */}
      <div className="mb-4 rounded-lg border border-border-default bg-bg-surface p-4">
        <div className="mb-3 flex items-center gap-2">
          <Lock size={16} className="text-text-secondary" />
          <h2 className="font-medium">Seguridad</h2>
        </div>

        {!changingPin ? (
          <button
            onClick={() => {
              setChangingPin(true);
              setPinMsg(null);
            }}
            className="text-sm text-accent hover:text-accent-hover"
          >
            Cambiar PIN
          </button>
        ) : (
          <form onSubmit={handleChangePin} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-text-secondary">PIN actual</label>
              <input
                type="password"
                inputMode="numeric"
                maxLength={6}
                value={currentPin}
                onChange={(e) => setCurrentPin(e.target.value.replace(/\D/g, ""))}
                className="w-full rounded-lg border border-border-default bg-bg-primary px-3 py-2 text-sm outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-text-secondary">Nuevo PIN</label>
              <input
                type="password"
                inputMode="numeric"
                maxLength={6}
                value={newPin}
                onChange={(e) => setNewPin(e.target.value.replace(/\D/g, ""))}
                className="w-full rounded-lg border border-border-default bg-bg-primary px-3 py-2 text-sm outline-none focus:border-accent"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setChangingPin(false);
                  setCurrentPin("");
                  setNewPin("");
                }}
                className="rounded-lg border border-border-default px-3 py-1.5 text-sm text-text-secondary hover:bg-bg-surface-hover"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-accent px-3 py-1.5 text-sm font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
              >
                {saving ? "Guardando..." : "Guardar"}
              </button>
            </div>
          </form>
        )}

        {pinMsg && (
          <p className={`mt-2 text-sm ${pinMsg.type === "ok" ? "text-success" : "text-error"}`}>
            {pinMsg.text}
          </p>
        )}
      </div>

      {/* Logout */}
      <div className="rounded-lg border border-border-default bg-bg-surface p-4">
        <button
          onClick={() => {
            logout();
            window.location.replace("/");
          }}
          className="flex items-center gap-2 text-sm text-error hover:text-error/80"
        >
          <LogOut size={16} />
          Cerrar sesion
        </button>
      </div>
    </div>
  );
}
