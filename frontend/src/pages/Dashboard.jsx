import { useApi } from "../hooks/useApi";
import { getMetrics, getPerformance } from "../api";
import {
  LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";

function MetricCard({ label, value, delta, deltaType }) {
  const cls = deltaType === "pos" ? "delta-pos" : deltaType === "neg" ? "delta-neg" : "delta-neu";
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value ?? "—"}</div>
      {delta && <div className={`metric-delta ${cls}`}>{delta}</div>}
    </div>
  );
}

function fmt(n, type) {
  if (n == null) return "—";
  if (type === "pct")  return (n * 100).toFixed(2) + "%";
  if (type === "inr")  return "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
  if (type === "num")  return Number(n).toFixed(2);
  return String(n);
}

export default function Dashboard({ livePrices }) {
  const { data: metrics, loading: ml } = useApi(getMetrics, [], 60000);
  const { data: perf,    loading: pl } = useApi(getPerformance, [], 120000);

  const chartData = Array.isArray(perf) ? perf.slice() : [];

  return (
    <div>
      <div className="page-title">
        Dashboard
        <div className="page-sub">Strategy performance overview</div>
      </div>

      {/* Metric cards */}
      <div className="metric-grid">
        <MetricCard label="Final Equity"   value={fmt(metrics?.FinalEquity,  "inr")} />
        <MetricCard label="CAGR"           value={fmt(metrics?.CAGR,         "pct")}
                    delta={metrics?.CAGR > 0 ? "above zero" : "below zero"}
                    deltaType={metrics?.CAGR > 0 ? "pos" : "neg"} />
        <MetricCard label="Sharpe Ratio"   value={fmt(metrics?.Sharpe,       "num")}
                    deltaType={metrics?.Sharpe > 0.5 ? "pos" : "neg"} />
        <MetricCard label="Max Drawdown"   value={fmt(metrics?.MaxDrawdown,  "pct")}
                    deltaType="neg" />
        <MetricCard label="Win Rate"       value={fmt(metrics?.WinRate,      "pct")}
                    deltaType={metrics?.WinRate > 0.5 ? "pos" : "neg"} />
        <MetricCard label="Total Return"   value={fmt(metrics?.TotalReturn,  "pct")}
                    deltaType={metrics?.TotalReturn > 0 ? "pos" : "neg"} />
        <MetricCard label="Volatility"     value={fmt(metrics?.Volatility,   "pct")} />
        <MetricCard label="Sortino"        value={fmt(metrics?.Sortino,      "num")} />
      </div>

      {/* Equity curve */}
      <div className="section">
        <div className="section-title">Equity Curve</div>
        {pl
          ? <div className="loading">Loading…</div>
          : <ResponsiveContainer width="100%" height={240}>
              <LineChart data={chartData}>
                <CartesianGrid stroke="#2a2f3d" strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fill: "#8892a4", fontSize: 10 }} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: "#8892a4", fontSize: 10 }} tickLine={false} axisLine={false}
                       tickFormatter={v => "₹" + (v/100000).toFixed(0) + "L"} />
                <Tooltip
                  contentStyle={{ background: "#1c2030", border: "1px solid #2a2f3d", borderRadius: 6, fontSize: 12 }}
                  formatter={(v) => ["₹" + Number(v).toLocaleString("en-IN"), "Equity"]}
                />
                <Line type="monotone" dataKey="equity" stroke="#4a9eff" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
        }
      </div>

      {/* Drawdown */}
      <div className="section">
        <div className="section-title">Drawdown</div>
        {!pl && (
          <ResponsiveContainer width="100%" height={160}>
            <AreaChart data={chartData}>
              <CartesianGrid stroke="#2a2f3d" strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fill: "#8892a4", fontSize: 10 }} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fill: "#8892a4", fontSize: 10 }} tickLine={false} axisLine={false}
                     tickFormatter={v => (v * 100).toFixed(0) + "%"} />
              <Tooltip
                contentStyle={{ background: "#1c2030", border: "1px solid #2a2f3d", borderRadius: 6, fontSize: 12 }}
                formatter={(v) => [(v * 100).toFixed(2) + "%", "Drawdown"]}
              />
              <Area type="monotone" dataKey="drawdown" stroke="#ef4444" fill="rgba(239,68,68,0.15)" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Live prices ticker */}
      {livePrices?.length > 0 && (
        <div className="section">
          <div className="section-title">Live Prices</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
            {livePrices.map(p => (
              <div key={p.symbol} className="metric-card" style={{ minWidth: 110 }}>
                <div className="metric-label">{p.symbol}</div>
                <div className="metric-value" style={{ fontSize: 15 }}>₹{p.price?.toLocaleString("en-IN")}</div>
                <div className={`metric-delta ${p.change_pct >= 0 ? "delta-pos" : "delta-neg"}`}>
                  {p.change_pct >= 0 ? "+" : ""}{p.change_pct?.toFixed(2)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}