import { useCallback, useEffect, useState } from "react";

/** Carga de datos del dashboard admin: fetch con cancelación al desmontar y
 * recarga explícita vía reload(). Todos los setState ocurren tras el await
 * (nunca síncronos dentro del effect). El fetcher debe ser estable
 * (función de módulo o useCallback). */
export function useAdminData<T>(fetcher: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const d = await fetcher();
        if (!cancelled) {
          setData(d);
          setError("");
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Error al cargar");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [fetcher, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, error, setError, reload, loading: data === null && !error };
}
