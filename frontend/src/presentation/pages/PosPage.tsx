import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useProducts } from "../../application/hooks/useProducts";
import { useExchangeRate } from "../../application/hooks/useExchangeRate";
import { useCart } from "../../application/store/cartStore";
import { useInvoice } from "../../application/hooks/useInvoice";
import Cart from "../components/Cart";

export default function PosPage() {
  const { products, loading } = useProducts();
  const { rate } = useExchangeRate();
  const cartState = useCart();
  const { createInvoice, loading: invoiceLoading } = useInvoice();
  const navigate = useNavigate();
  const [showCart, setShowCart] = useState(false);

  const totalSats =
    rate && cartState.totalMxn > 0
      ? Math.round(cartState.totalMxn * (100_000_000 / rate.mxn_per_btc))
      : null;

  const handleCheckout = async () => {
    if (cartState.items.length === 0) return;
    const data = await createInvoice(cartState.items);
    if (data) {
      navigate(
        `/pos/pay?hash=${data.payment_hash}&bolt11=${encodeURIComponent(data.bolt11)}&mxn=${data.total_mxn}&sats=${data.total_sats}&expires=${data.expires_at}&sale=${data.sale_id}`
      );
    }
  };

  return (
    <div className="flex h-[calc(100dvh-64px)] flex-col md:flex-row md:gap-4">
      {/* Product grid */}
      <div className="flex-1 overflow-y-auto">
        <div className="mb-3 flex items-center justify-between">
          <h1 className="text-lg font-bold">POS</h1>
          {rate ? (
            <span className="font-mono text-xs text-text-secondary">
              1 BTC = ${rate.mxn_per_btc.toLocaleString()} MXN
            </span>
          ) : (
            <span className="text-xs text-warning">Sin tipo de cambio</span>
          )}
        </div>

        {loading ? (
          <p className="text-text-secondary">Cargando productos...</p>
        ) : products.length === 0 ? (
          <div className="mt-16 text-center">
            <p className="text-text-secondary">No hay productos.</p>
            <p className="text-sm text-text-secondary">
              Agrega productos en la seccion de Productos.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {products.map((p) => (
              <button
                key={p.id}
                onClick={() => cartState.add(p)}
                className="flex flex-col items-center justify-center rounded-lg border border-border-default bg-bg-surface p-4 text-center transition-colors hover:bg-bg-surface-hover active:border-accent"
              >
                <span className="mb-1 text-sm font-medium">{p.name}</span>
                <span className="font-mono text-accent">
                  ${p.price_mxn.toFixed(2)}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Cart — sidebar on tablet+, bottom sheet toggle on mobile */}
      <div className="hidden w-72 shrink-0 rounded-lg border border-border-default bg-bg-surface p-4 md:flex md:flex-col">
        <Cart
          items={cartState.items}
          totalMxn={cartState.totalMxn}
          totalSats={totalSats}
          onUpdateQuantity={cartState.updateQuantity}
          onRemove={cartState.remove}
          onCheckout={handleCheckout}
          onClear={cartState.clear}
          checkoutDisabled={invoiceLoading || cartState.items.length === 0}
        />
      </div>

      {/* Mobile: floating cart button + bottom sheet */}
      {cartState.count > 0 && !showCart && (
        <button
          onClick={() => setShowCart(true)}
          className="fixed bottom-20 right-4 z-40 flex items-center gap-2 rounded-full bg-accent px-5 py-3 font-bold text-bg-primary shadow-lg md:hidden"
        >
          Carrito ({cartState.count}) · ${cartState.totalMxn.toFixed(2)}
        </button>
      )}

      {showCart && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setShowCart(false)}
          />
          <div className="absolute inset-x-0 bottom-0 max-h-[70dvh] overflow-y-auto rounded-t-xl bg-bg-surface p-4">
            <Cart
              items={cartState.items}
              totalMxn={cartState.totalMxn}
              totalSats={totalSats}
              onUpdateQuantity={cartState.updateQuantity}
              onRemove={cartState.remove}
              onCheckout={() => {
                setShowCart(false);
                handleCheckout();
              }}
              onClear={cartState.clear}
              checkoutDisabled={invoiceLoading || cartState.items.length === 0}
            />
          </div>
        </div>
      )}
    </div>
  );
}
