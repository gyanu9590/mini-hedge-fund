import { useCallback, useEffect, useState } from "react";

/**
 * useApi(fetchFn, deps, refreshInterval)
 * Generic hook for any API call. Handles loading, error, and auto-refresh.
 *
 * Usage:
 *   const { data, loading, error, refresh } = useApi(getMetrics, [], 30000);
 */
export function useApi(fetchFn, deps = [], refreshInterval = null) {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const fetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetchFn();
      setData(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    fetch();
    if (refreshInterval) {
      const id = setInterval(fetch, refreshInterval);
      return () => clearInterval(id);
    }
  }, [fetch]);

  return { data, loading, error, refresh: fetch };
}