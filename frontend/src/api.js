import axios from "axios";

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "X-API-Key": import.meta.env.VITE_API_KEY || "changeme",
    "Content-Type": "application/json",
  },
});

API.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("[API]", err.response?.status, err.config?.url);
    return Promise.reject(err);
  }
);

// ── Endpoints ─────────────────────────────────────────────────────────────────
export const getHealth        = ()       => API.get("/health/detailed");
export const getMetrics       = ()       => API.get("/metrics");
export const getPerformance   = ()       => API.get("/performance");
export const getSignalsToday  = ()       => API.get("/signals/today");
export const getOrders        = ()       => API.get("/orders");
export const getRisk          = ()       => API.get("/risk");
export const getMarketOverview= ()       => API.get("/market/overview");
export const getLivePrices    = ()       => API.get("/live-prices");
export const getMarketData    = (symbol) => API.get(`/market/${symbol}`);
export const getSettings      = ()       => API.get("/settings");
export const saveSettings     = (body)   => API.post("/settings", body);
export const runPipeline      = ()       => API.post("/pipeline/run");
export const getPipelineStatus= ()       => API.get("/pipeline/status");

export default API;