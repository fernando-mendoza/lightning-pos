import { useCallback, useEffect, useState } from "react";
import { api } from "../../infrastructure/api";
import type { Product } from "../../domain/types";

export function useProducts() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.products.list();
      setProducts(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error loading products");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = async (name: string, price_mxn: number) => {
    await api.products.create({ name, price_mxn });
    await refresh();
  };

  const update = async (id: string, name: string, price_mxn: number) => {
    await api.products.update(id, { name, price_mxn });
    await refresh();
  };

  const remove = async (id: string) => {
    await api.products.remove(id);
    await refresh();
  };

  return { products, loading, error, create, update, remove, refresh };
}
