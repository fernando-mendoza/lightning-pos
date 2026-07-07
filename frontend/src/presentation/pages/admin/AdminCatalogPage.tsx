import { useState } from "react";
import { Pencil, Plus, RotateCcw, Trash2 } from "lucide-react";
import { useAdminData } from "../../../application/hooks/useAdminData";
import { adminApi, type AdminProduct } from "../../../infrastructure/adminApi";

interface FormState {
  id: string | null;
  name: string;
  price: string;
  barcode: string;
}

const EMPTY: FormState = { id: null, name: "", price: "", barcode: "" };

export default function AdminCatalogPage() {
  const { data, error, setError, reload, loading } = useAdminData(adminApi.products.list);
  const products = data ?? [];
  const [form, setForm] = useState<FormState | null>(null);
  const [busy, setBusy] = useState(false);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form) return;
    setBusy(true);
    try {
      const data = {
        name: form.name.trim(),
        price_mxn: form.price,
        barcode: form.barcode.trim() || null,
      };
      if (form.id) await adminApi.products.update(form.id, data);
      else await adminApi.products.create(data);
      setForm(null);
      reload();
    } catch (err) {
      setError(
        err instanceof Error && err.message === "barcode_exists"
          ? "Ya existe un producto con ese código de barras."
          : "No se pudo guardar el producto."
      );
    } finally {
      setBusy(false);
    }
  };

  const softDelete = async (p: AdminProduct) => {
    if (!confirm(`¿Desactivar "${p.name}"?`)) return;
    await adminApi.products.remove(p.id);
    reload();
  };

  const reactivate = async (p: AdminProduct) => {
    await adminApi.products.update(p.id, { active: true });
    reload();
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Catálogo</h1>
        <button
          onClick={() => setForm(EMPTY)}
          data-testid="admin-product-new"
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover"
        >
          <Plus size={16} />
          Nuevo
        </button>
      </div>

      {error && <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">{error}</p>}

      {form && (
        <form
          onSubmit={save}
          className="mb-4 flex flex-col gap-3 rounded-lg border border-border-default bg-bg-surface p-4"
        >
          <p className="font-medium">{form.id ? "Editar producto" : "Nuevo producto"}</p>
          <input
            required
            placeholder="Nombre"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            data-testid="admin-product-name"
            className="rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
          />
          <div className="flex gap-3">
            <input
              required
              type="number"
              step="0.01"
              min="0"
              placeholder="Precio MXN"
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
              data-testid="admin-product-price"
              className="w-40 rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
            />
            <input
              placeholder="Código de barras (opcional)"
              value={form.barcode}
              onChange={(e) => setForm({ ...form, barcode: e.target.value })}
              className="flex-1 rounded-lg border border-border-default bg-bg-primary px-3 py-2 outline-none focus:border-accent"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              data-testid="admin-product-save"
              className="rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
            >
              Guardar
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
      ) : products.length === 0 ? (
        <div className="mt-16 text-center">
          <p className="text-text-secondary">No hay productos aún.</p>
          <p className="text-sm text-text-secondary">Las terminales cobran del catálogo o con monto libre.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {products.map((p) => (
            <div
              key={p.id}
              className={`flex items-center justify-between rounded-lg border border-border-default bg-bg-surface px-4 py-3 ${
                p.active ? "" : "opacity-50"
              }`}
            >
              <div>
                <p className="font-medium">
                  {p.name}
                  {!p.active && <span className="ml-2 text-xs text-text-secondary">(inactivo)</span>}
                </p>
                <p className="text-sm text-text-secondary">
                  ${Number(p.price_mxn).toFixed(2)} MXN
                  {p.barcode ? ` · ${p.barcode}` : ""}
                </p>
              </div>
              <div className="flex gap-1">
                {p.active ? (
                  <>
                    <button
                      onClick={() => setForm({ id: p.id, name: p.name, price: p.price_mxn, barcode: p.barcode ?? "" })}
                      aria-label={`Editar ${p.name}`}
                      className="rounded-lg p-2 text-text-secondary hover:bg-bg-primary hover:text-text-primary"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      onClick={() => void softDelete(p)}
                      aria-label={`Desactivar ${p.name}`}
                      className="rounded-lg p-2 text-text-secondary hover:bg-bg-primary hover:text-error"
                    >
                      <Trash2 size={16} />
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => void reactivate(p)}
                    aria-label={`Reactivar ${p.name}`}
                    className="flex items-center gap-1.5 rounded-lg border border-border-default px-3 py-1.5 text-sm text-text-secondary hover:border-accent hover:text-text-primary"
                  >
                    <RotateCcw size={14} />
                    Reactivar
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
