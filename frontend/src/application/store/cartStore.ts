import { useSyncExternalStore } from "react";
import type { Product, CartItem } from "../../domain/types";

let items: CartItem[] = [];
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export const cart = {
  add(product: Product) {
    const existing = items.find((i) => i.product.id === product.id);
    if (existing) {
      items = items.map((i) =>
        i.product.id === product.id ? { ...i, quantity: i.quantity + 1 } : i
      );
    } else {
      items = [...items, { product, quantity: 1 }];
    }
    emit();
  },

  remove(productId: string) {
    items = items.filter((i) => i.product.id !== productId);
    emit();
  },

  updateQuantity(productId: string, quantity: number) {
    if (quantity <= 0) {
      cart.remove(productId);
      return;
    }
    items = items.map((i) =>
      i.product.id === productId ? { ...i, quantity } : i
    );
    emit();
  },

  clear() {
    items = [];
    emit();
  },

  getItems(): CartItem[] {
    return items;
  },

  getTotalMxn(): number {
    return items.reduce((sum, i) => sum + i.product.price_mxn * i.quantity, 0);
  },

  getCount(): number {
    return items.reduce((sum, i) => sum + i.quantity, 0);
  },
};

export function useCart() {
  const snapshot = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => items
  );

  return {
    items: snapshot,
    totalMxn: cart.getTotalMxn(),
    count: cart.getCount(),
    add: cart.add,
    remove: cart.remove,
    updateQuantity: cart.updateQuantity,
    clear: cart.clear,
  };
}
