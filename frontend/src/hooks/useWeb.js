import { useEffect, useRef, useState } from "react";

/**
 * useWebSocket
 * Connects to the FastAPI WebSocket endpoint and returns live price data.
 * Auto-reconnects every 3 seconds if connection drops.
 *
 * Usage:
 *   const { prices, connected } = useWebSocket();
 */
export function useWebSocket() {
  const [prices, setPrices]       = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef   = useRef(null);
  const retryRef = useRef(null);

  const WS_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000")
    .replace("https://", "wss://")
    .replace("http://",  "ws://")
    + "/ws/prices";

  function connect() {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen  = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      // Retry after 3 seconds
      retryRef.current = setTimeout(connect, 3000);
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "prices") setPrices(msg.data);
      } catch {}
    };
  }

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, []);

  return { prices, connected };
}