import { useState } from "react";
import { Minus, Plus, Trash2 } from "lucide-react";
import type { CartItem } from "../../domain/types";

interface Props {
  items: CartItem[];
  subtotalMxn: number;
  satsPerMxn: number | null;
  onUpdateQuantity: (productId: string, quantity: number) => void;
  onRemove: (productId: string) => void;
  onCheckout: (tipMxn: number, discountMxn: number) => void;
  onClear: () => void;
  checkoutDisabled: boolean;
}

const TIP_PRESETS = [0, 5, 10, 15] as const;

function parsePositiveNumber(input: string): number {
  const n = parseFloat(input);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

export default function Cart({
  items,
  subtotalMxn,
  satsPerMxn,
  onUpdateQuantity,
  onRemove,
  onCheckout,
  onClear,
  checkoutDisabled,
}: Props) {
  const [tipPct, setTipPct] = useState<number>(0);
  const [tipCustomInput, setTipCustomInput] = useState("");
  const [discountInput, setDiscountInput] = useState("");

  const resetCharges = () => {
    setTipPct(0);
    setTipCustomInput("");
    setDiscountInput("");
  };

  const handleClear = () => {
    resetCharges();
    onClear();
  };

  if (items.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-text-secondary">
        <p className="text-sm">Carrito vacio</p>
        <p className="text-xs">Toca un producto para agregar</p>
      </div>
    );
  }

  const rawDiscount = parsePositiveNumber(discountInput);
  const discountMxn = Math.min(rawDiscount, subtotalMxn);
  const baseForTip = Math.max(0, subtotalMxn - discountMxn);

  const tipFromCustom = parsePositiveNumber(tipCustomInput);
  const tipMxn =
    tipFromCustom > 0 ? tipFromCustom : (baseForTip * tipPct) / 100;

  const totalMxn = Math.max(0, baseForTip + tipMxn);
  const totalSats = satsPerMxn !== null ? Math.round(totalMxn * satsPerMxn) : null;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-bold uppercase tracking-wide text-text-secondary">
          Carrito ({items.reduce((s, i) => s + i.quantity, 0)})
        </h2>
        <button
          onClick={handleClear}
          className="text-xs text-text-secondary hover:text-error"
        >
          Limpiar
        </button>
      </div>

      {/* Items */}
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

      {/* Discount + tip controls */}
      <div className="mt-3 space-y-2 border-t border-border-default pt-3">
        <label className="flex items-center justify-between gap-2 text-xs">
          <span className="text-text-secondary">Descuento MXN</span>
          <input
            type="number"
            min={0}
            step="0.01"
            inputMode="decimal"
            placeholder="0.00"
            value={discountInput}
            onChange={(e) => setDiscountInput(e.target.value)}
            className="w-24 rounded-md border border-border-default bg-bg-primary px-2 py-1 text-right font-mono text-sm focus:border-accent focus:outline-none"
          />
        </label>

        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs text-text-secondary">Propina</span>
            <input
              type="number"
              min={0}
              step="0.01"
              inputMode="decimal"
              placeholder="custom $"
              value={tipCustomInput}
              onChange={(e) => {
                setTipCustomInput(e.target.value);
                if (e.target.value) setTipPct(0);
              }}
              className="w-24 rounded-md border border-border-default bg-bg-primary px-2 py-1 text-right font-mono text-xs focus:border-accent focus:outline-none"
            />
          </div>
          <div className="flex gap-1">
            {TIP_PRESETS.map((pct) => {
              const active = tipPct === pct && !tipCustomInput;
              return (
                <button
                  key={pct}
                  onClick={() => {
                    setTipPct(pct);
                    setTipCustomInput("");
                  }}
                  className={`flex-1 rounded-md py-1 text-xs font-medium transition-colors ${
                    active
                      ? "bg-accent text-bg-primary"
                      : "bg-bg-primary text-text-secondary hover:bg-bg-surface-hover"
                  }`}
                >
                  {pct === 0 ? "—" : `${pct}%`}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Breakdown + total */}
      <div className="mt-3 space-y-1 border-t border-border-default pt-3 text-xs">
        <div className="flex justify-between text-text-secondary">
          <span>Subtotal</span>
          <span className="font-mono">${subtotalMxn.toFixed(2)}</span>
        </div>
        {discountMxn > 0 && (
          <div className="flex justify-between text-text-secondary">
            <span>Descuento</span>
            <span className="font-mono">-${discountMxn.toFixed(2)}</span>
          </div>
        )}
        {tipMxn > 0 && (
          <div className="flex justify-between text-text-secondary">
            <span>
              Propina
              {tipFromCustom === 0 && tipPct > 0 ? ` (${tipPct}%)` : ""}
            </span>
            <span className="font-mono">+${tipMxn.toFixed(2)}</span>
          </div>
        )}
        <div className="flex justify-between pt-1 text-sm">
          <span className="text-text-secondary">Total</span>
          <span className="font-mono font-bold">${totalMxn.toFixed(2)} MXN</span>
        </div>
        {totalSats !== null && (
          <div className="flex justify-end">
            <span className="font-mono text-accent">
              {totalSats.toLocaleString()} sats
            </span>
          </div>
        )}
      </div>

      <button
        onClick={() => onCheckout(tipMxn, discountMxn)}
        disabled={checkoutDisabled || totalMxn <= 0}
        className="mt-3 w-full rounded-lg bg-accent py-3 text-center font-bold text-bg-primary hover:bg-accent-hover disabled:opacity-50"
      >
        Cobrar
      </button>
    </div>
  );
}
