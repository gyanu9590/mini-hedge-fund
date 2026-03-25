import axios from "axios";

// Base API client — reads API key from env or falls back to default
const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "X-API-Key": import.meta.env.VITE_API_KEY || "changeme",
    "Content-Type": "application/json",
  },
});

// ── Request interceptor for logging ──────────────────────────────────────────
API.interceptors.request.use((config) => {
  console.debug(`[API] ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// ── Response interceptor for error handling ───────────────────────────────────
API.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("[API Error]", err.response?.status, err.response?.data);
    return Promise.reject(err);
  }
);

// ── Endpoints ─────────────────────────────────────────────────────────────────
export const getHealth      = ()       => API.get("/health");
export const getSignals     = ()       => API.get("/signals");
export const getOrders      = ()       => API.get("/orders");
export const getPerformance = ()       => API.get("/performance");
export const getMetrics     = ()       => API.get("/metrics");
export const getRisk        = ()       => API.get("/risk");
export const getLivePrices  = ()       => API.get("/live-prices");
export const getMarketData  = (symbol) => API.get(`/market/${symbol}`);

export default API;