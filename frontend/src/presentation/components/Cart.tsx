import { Minus, Plus, Trash2 } from "lucide-react";
import type { CartItem } from "../../domain/types";

interface Props {
  items: CartItem[];
  totalMxn: number;
  totalSats: number | null;
  onUpdateQuantity: (productId: string, quantity: number) => void;
  onRemove: (productId: string) => void;
  onCheckout: () => void;
  onClear: () => void;
  checkoutDisabled: boolean;
}

export default function Cart({
  items,
  totalMxn,
  totalSats,
  onUpdateQuantity,
  onRemove,
  onCheckout,
  onClear,
  checkoutDisabled,
}: Props) {
  if (items.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-text-secondary">
        <p className="text-sm">Carrito vacio</p>
        <p className="text-xs">Toca un producto para agregar</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide text-text-secondary">
          Carrito ({items.reduce((s, i) => s + i.quantity, 0)})
        </h2>
        <button
          onClick={onClear}
          className="text-xs text-text-secondary hover:text-error"
        >
          Limpiar
        </button>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto">
        {items.map((item) => (
          <div
            key={item.product.id}
            className="flex items-center justify-between rounded-lg bg-bg-primary px-3 py-2"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{item.product.name}</p>
              <p className="font-mono text-xs text-text-secondary">
                ${(item.product.price_mxn * item.quantity).toFixed(2)}
              </p>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() =>
                  onUpdateQuantity(item.product.id, item.quantity - 1)
                }
                className="rounded p-1 text-text-secondary hover:bg-bg-surface-hover"
              >
                <Minus size={14} />
              </button>
              <span className="w-6 text-center font-mono text-sm">
                {item.quantity}
              </span>
              <button
                onClick={() =>
                  onUpdateQuantity(item.product.id, item.quantity + 1)
                }
                className="rounded p-1 text-text-secondary hover:bg-bg-surface-hover"
              >
                <Plus size={14} />
              </button>
              <button
                onClick={() => onRemove(item.product.id)}
                className="ml-1 rounded p-1 text-text-secondary hover:text-error"
              >
                <Trash2 size={14} />
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 border-t border-border-default pt-3">
        <div className="flex justify-between text-sm">
          <span className="text-text-secondary">Total</span>
          <span className="font-mono font-bold">${totalMxn.toFixed(2)} MXN</span>
        </div>
        {totalSats !== null && (
          <div className="flex justify-between text-sm">
            <span></span>
            <span className="font-mono text-accent">
              {totalSats.toLocaleString()} sats
            </span>
          </div>
        )}
        <button
          onClick={onCheckout}
          disabled={checkoutDisabled}
          className="mt-3 w-full rounded-lg bg-accent py-3 text-center font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
        >
          Cobrar
        </button>
      </div>
    </div>
  );
}
