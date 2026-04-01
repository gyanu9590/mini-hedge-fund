import { useState } from "react";
import Dashboard   from "./pages/Dashboard";
import Signals     from "./pages/Signals";
import Orders      from "./pages/Orders";
import Portfolio  from "./pages/portfolio";
import RiskPage    from "./pages/RiskPage";
import MarketPage  from "./pages/MarketPage";
import SystemPage  from "./pages/SystemPage";
import { useWebSocket } from "./hooks/useWeb";
import "./App.css";

const NAV = [
  { id: "dashboard", label: "Dashboard"  },
  { id: "signals",   label: "Signals"    },
  { id: "orders",    label: "Orders"     },
  { id: "risk",      label: "Risk"       },
  { id: "market",    label: "Market"     },
  { id: "system",    label: "System"     },
  { id: "portfolio",  label: "Portfolio"   },
];

export default function App() {
  const [page, setPage] = useState("dashboard");
  const { prices, connected } = useWebSocket();

  const pages = {
    dashboard: <Dashboard livePrices={prices} />,
    signals:   <Signals />,
    orders:    <Orders  livePrices={prices} />,
    Portfolio:  <Portfolio />,
    risk:      <RiskPage />,
    market:    <MarketPage livePrices={prices} />,
    system:    <SystemPage />,
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-dot" />
          QuantEdge
        </div>

        <nav className="sidebar-nav">
          {NAV.map(n => (
            <button
              key={n.id}
              className={`nav-item ${page === n.id ? "active" : ""}`}
              onClick={() => setPage(n.id)}
            >
              {n.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className={`ws-dot ${connected ? "on" : "off"}`} />
          {connected ? "Live" : "Reconnecting…"}
        </div>
      </aside>

      {/* Main content */}
      <main className="main">
        {pages[page]}
      </main>
    </div>
  );
}