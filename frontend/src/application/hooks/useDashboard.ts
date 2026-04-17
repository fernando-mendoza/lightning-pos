import { useEffect, useState } from "react";
import { getToken, clearSessionAndReload } from "./useAuth";

export interface DailyEntry {
  date: string;
  total_mxn: number;
  total_sats: number;
  count: number;
}

export interface DaySummary {
  total_mxn: number;
  total_sats: number;
  count: number;
}

export interface TopProduct {
  name: string;
  quantity: number;
  total_mxn: number;
}

export interface DashboardSummary {
  today: DaySummary;
  last_7_days: DailyEntry[];
  top_products: TopProduct[];
}

export function useDashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const token = getToken();
        const res = await fetch("/api/dashboard/summary", {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (res.status === 401 && token) {
          clearSessionAndReload();
          return;
        }
        if (!res.ok) throw new Error(`${res.status}`);
        const json: DashboardSummary = await res.json();
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Error loading dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    return () => {
      cancelled = true;
    };
  }, []);

  return { data, loading, error };
}
