import { useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { useProducts } from "../../application/hooks/useProducts";
import ProductModal from "../components/ProductModal";
import type { Product } from "../../domain/types";

export default function ProductsPage() {
  const { products, loading, error, create, update, remove } = useProducts();
  const [modal, setModal] = useState<{ open: boolean; product?: Product | null }>({
    open: false,
  });
  const [deleting, setDeleting] = useState<string | null>(null);

  const handleDelete = async (product: Product) => {
    if (!confirm(`Eliminar "${product.name}"?`)) return;
    setDeleting(product.id);
    try {
      await remove(product.id);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Productos</h1>
        <button
          onClick={() => setModal({ open: true, product: null })}
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-bold text-bg-primary hover:bg-accent-hover"
        >
          <Plus size={16} />
          Nuevo
        </button>
      </div>

      {error && (
        <p className="mb-4 rounded-lg bg-error/10 px-4 py-2 text-sm text-error">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-text-secondary">Cargando...</p>
      ) : products.length === 0 ? (
        <div className="mt-16 text-center">
          <p className="text-text-secondary">No hay productos aun.</p>
          <p className="text-sm text-text-secondary">
            Agrega tu primer producto para comenzar.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {products.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between rounded-lg border border-border-default bg-bg-surface px-4 py-3"
            >
              <div>
                <p className="font-medium">{p.name}</p>
                <p className="font-mono text-sm text-accent">
                  ${p.price_mxn.toFixed(2)} MXN
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setModal({ open: true, product: p })}
                  className="rounded-lg p-2 text-text-secondary hover:bg-bg-surface-hover hover:text-text-primary"
                >
                  <Pencil size={16} />
                </button>
                <button
                  onClick={() => handleDelete(p)}
                  disabled={deleting === p.id}
                  className="rounded-lg p-2 text-text-secondary hover:bg-error/10 hover:text-error disabled:opacity-50"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modal.open && (
        <ProductModal
          product={modal.product}
          onSave={async (name, price_mxn) => {
            if (modal.product) {
              await update(modal.product.id, name, price_mxn);
            } else {
              await create(name, price_mxn);
            }
          }}
          onClose={() => setModal({ open: false })}
        />
      )}
    </div>
  );
}
