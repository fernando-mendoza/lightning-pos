import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import type { Product } from "../../domain/types";

interface Props {
  product?: Product | null;
  onSave: (name: string, price_mxn: number) => Promise<void>;
  onClose: () => void;
}

export default function ProductModal({ product, onSave, onClose }: Props) {
  const [name, setName] = useState(product?.name ?? "");
  const [price, setPrice] = useState(product?.price_mxn?.toString() ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    nameRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    const parsed = parseFloat(price);
    if (!trimmed) {
      setError("Nombre requerido");
      return;
    }
    if (isNaN(parsed) || parsed <= 0) {
      setError("Precio debe ser mayor a 0");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSave(trimmed, parsed);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-xl bg-bg-surface border border-border-default p-6"
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">
            {product ? "Editar producto" : "Nuevo producto"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-text-secondary hover:text-text-primary"
          >
            <X size={20} />
          </button>
        </div>

        <label className="mb-1 block text-sm font-medium text-text-secondary">
          Nombre
        </label>
        <input
          ref={nameRef}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mb-4 w-full rounded-lg border border-border-default bg-bg-primary px-3 py-2 text-text-primary outline-none focus:border-accent"
          placeholder="Ej: Cafe americano"
        />

        <label className="mb-1 block text-sm font-medium text-text-secondary">
          Precio (MXN)
        </label>
        <input
          type="number"
          step="0.01"
          min="0.01"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          className="mb-4 w-full rounded-lg border border-border-default bg-bg-primary px-3 py-2 text-text-primary outline-none focus:border-accent"
          placeholder="0.00"
        />

        {error && (
          <p className="mb-3 text-sm text-error">{error}</p>
        )}

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-lg border border-border-default px-4 py-2 text-sm font-medium text-text-secondary hover:bg-bg-surface-hover"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={saving}
            className="flex-1 rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
          >
            {saving ? "Guardando..." : "Guardar"}
          </button>
        </div>
      </form>
    </div>
  );
}
