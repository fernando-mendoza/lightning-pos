import { useCallback, useEffect, useState } from "react";
import type { Sale } from "../../domain/types";

export function useSales(date: string) {
  const [sales, setSales] = useState<Sale[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`/api/sales?date=${date}`);
      if (!res.ok) throw new Error(`${res.status}`);
      setSales(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error loading sales");
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const totalMxn = sales.reduce((s, sale) => s + sale.total_mxn, 0);
  const totalSats = sales.reduce((s, sale) => s + sale.total_sats, 0);

  return { sales, loading, error, totalMxn, totalSats, count: sales.length };
}
