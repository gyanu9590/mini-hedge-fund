// ── Orders ────────────────────────────────────────────────────────────────────
import { useApi } from "../hooks/useApi";
import { getOrders, getRisk, getMarketOverview, getMarketData, getSettings, saveSettings, runPipeline, getPipelineStatus } from "../api";
import { useState, useEffect } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

export function Orders({ livePrices }) {
  const { data, loading, error } = useApi(getOrders, [], 30000);

  const priceMap = Object.fromEntries((livePrices || []).map(p => [p.symbol, p.price]));

  return (
    <div>
      <div className="page-title">Orders<div className="page-sub">Latest sized orders from portfolio optimizer</div></div>
      {loading && <div className="loading">Loading…</div>}
      {error   && <div className="error">{error}</div>}
      {data && (
        <>
          <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
            {[
              { label: "BUY orders",  val: data.filter(r=>r.side==="BUY").length },
              { label: "SELL orders", val: data.filter(r=>r.side==="SELL").length },
              { label: "Total exposure", val: "₹" + data.reduce((s,r)=>s+Math.abs(r.target_value||0),0).toLocaleString("en-IN",{maximumFractionDigits:0}) },
            ].map(m => (
              <div key={m.label} className="metric-card" style={{ flex: 1 }}>
                <div className="metric-label">{m.label}</div>
                <div className="metric-value" style={{ fontSize: 18 }}>{m.val}</div>
              </div>
            ))}
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Entry ₹</th><th>Live ₹</th><th>P&L</th><th>Weight</th></tr></thead>
              <tbody>
                {data.map((r,i) => {
                  const live = priceMap[r.symbol];
                  const pnl  = live && r.price ? ((live - r.price) / r.price * 100).toFixed(2) : null;
                  return (
                    <tr key={i}>
                      <td style={{color:"var(--muted)"}}>{String(r.date||"").split("T")[0]}</td>
                      <td style={{fontWeight:600}}>{r.symbol}</td>
                      <td><span className={`badge badge-${r.side?.toLowerCase()}`}>{r.side}</span></td>
                      <td>{r.qty}</td>
                      <td>₹{Number(r.price||0).toLocaleString("en-IN",{maximumFractionDigits:2})}</td>
                      <td>{live ? "₹"+live.toLocaleString("en-IN") : <span style={{color:"var(--muted)"}}>—</span>}</td>
                      <td style={{color: pnl>0?"var(--green)":pnl<0?"var(--red)":"var(--muted)"}}>
                        {pnl != null ? (pnl > 0 ? "+" : "") + pnl + "%" : "—"}
                      </td>
                      <td style={{color:"var(--muted)"}}>{r.weight != null ? (r.weight*100).toFixed(1)+"%" : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

// ── Risk ──────────────────────────────────────────────────────────────────────
export function RiskPage() {
  const { data, loading, error } = useApi(getRisk, [], 60000);
  return (
    <div>
      <div className="page-title">Risk Analytics<div className="page-sub">VaR, CVaR, Drawdown</div></div>
      {loading && <div className="loading">Loading…</div>}
      {error   && <div className="error">{error}</div>}
      {data && (
        <div className="metric-grid">
          {[
            { label: "Daily VaR 95%",      val: (data.var_95*100).toFixed(2)+"%",        type:"neg" },
            { label: "CVaR 95%",           val: (data.cvar_95*100).toFixed(2)+"%",       type:"neg" },
            { label: "Max Drawdown",       val: (data.max_drawdown*100).toFixed(2)+"%",  type:"neg" },
            { label: "Current Drawdown",   val: (data.current_drawdown*100).toFixed(2)+"%", type: data.current_drawdown<-0.05?"neg":"neu" },
            { label: "Positive Days",      val: (data.positive_days*100).toFixed(1)+"%", type:"pos" },
          ].map(m => (
            <div key={m.label} className="metric-card">
              <div className="metric-label">{m.label}</div>
              <div className={`metric-value delta-${m.type}`} style={{fontSize:18}}>{m.val}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Market ────────────────────────────────────────────────────────────────────
export function MarketPage({ livePrices }) {
  const { data: overview } = useApi(getMarketOverview, [], 60000);
  const [symbol, setSymbol] = useState("TCS");
  const { data: candles }   = useApi(() => getMarketData(symbol), [symbol]);

  return (
    <div>
      <div className="page-title">Market Terminal</div>
      {overview && (
        <div className="metric-grid" style={{marginBottom:24}}>
          {overview.map(m => (
            <div key={m.name} className="metric-card">
              <div className="metric-label">{m.name}</div>
              <div className="metric-value" style={{fontSize:16}}>{m.price ?? "—"}</div>
              <div className={`metric-delta ${m.change_pct>=0?"delta-pos":"delta-neg"}`}>
                {m.change_pct>=0?"+":""}{m.change_pct?.toFixed(2)}%
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{marginBottom:16, display:"flex", gap:10, alignItems:"center"}}>
        <span style={{color:"var(--muted)", fontSize:12}}>Symbol:</span>
        {["TCS","INFY","RELIANCE","HDFCBANK","ICICIBANK","SBIN","ITC","AXISBANK"].map(s => (
          <button key={s} onClick={()=>setSymbol(s)}
            className="btn"
            style={{fontSize:11, padding:"4px 10px", background: symbol===s?"var(--accent)":"", color: symbol===s?"#fff":""}}>
            {s}
          </button>
        ))}
      </div>

      {candles && Array.isArray(candles) && candles.length > 0 && (
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={candles.slice(-120)}>
            <CartesianGrid stroke="#2a2f3d" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{fill:"#8892a4",fontSize:9}} tickLine={false} interval={20} />
            <YAxis tick={{fill:"#8892a4",fontSize:10}} tickLine={false} axisLine={false} domain={["auto","auto"]} />
            <Tooltip contentStyle={{background:"#1c2030",border:"1px solid #2a2f3d",borderRadius:6,fontSize:12}}
              formatter={v=>["₹"+Number(v).toLocaleString("en-IN"),"Close"]} />
            <Bar dataKey="close" fill="#4a9eff" radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
      )}

      {livePrices?.length > 0 && (
        <div className="section" style={{marginTop:24}}>
          <div className="section-title">Live Prices (WebSocket)</div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Symbol</th><th>Price</th><th>Change</th></tr></thead>
              <tbody>
                {livePrices.map(p => (
                  <tr key={p.symbol}>
                    <td style={{fontWeight:600}}>{p.symbol}</td>
                    <td>₹{p.price?.toLocaleString("en-IN")}</td>
                    <td className={p.change_pct>=0?"delta-pos":"delta-neg"}>
                      {p.change_pct>=0?"+":""}{p.change_pct?.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ── System ────────────────────────────────────────────────────────────────────
export function SystemPage() {
  const { data: health } = useApi(() => fetch("/health/detailed").then(r=>r.json()), [], 30000);
  const [pipeStatus, setPipeStatus] = useState(null);
  const [running, setRunning]       = useState(false);

  async function handleRunPipeline() {
    setRunning(true);
    try {
      await runPipeline();
      // Poll status every 2s
      const id = setInterval(async () => {
        try {
          const res = await getPipelineStatus();
          setPipeStatus(res.data);
          if (!res.data.running) {
            clearInterval(id);
            setRunning(false);
          }
        } catch { clearInterval(id); setRunning(false); }
      }, 2000);
    } catch (e) {
      setRunning(false);
    }
  }

  return (
    <div>
      <div className="page-title">System<div className="page-sub">Pipeline control and health checks</div></div>

      <div className="section">
        <div className="section-title">Run Pipeline</div>
        <button className="btn btn-primary" onClick={handleRunPipeline} disabled={running}>
          {running ? `Running: ${pipeStatus?.step || "…"}` : "Run Full Pipeline"}
        </button>
        {pipeStatus?.error && <div className="error" style={{marginTop:10}}>{pipeStatus.error}</div>}
        {pipeStatus?.step === "Done" && <div style={{color:"var(--green)",marginTop:10,fontSize:12}}>Pipeline completed successfully</div>}
      </div>

      {health?.checks && (
        <div className="section">
          <div className="section-title">Data Health</div>
          <div className="metric-grid">
            {Object.entries(health.checks).map(([k,v]) => (
              <div key={k} className="metric-card">
                <div className="metric-label">{k}</div>
                <div className={`metric-value ${v?"delta-pos":"delta-neg"}`} style={{fontSize:14}}>
                  {v ? "OK" : "Missing"}
                </div>
              </div>
            ))}
          </div>
          {health.latest_signal_date && (
            <div style={{color:"var(--muted)",fontSize:12,marginTop:8}}>
              Latest signal date: <strong style={{color:"var(--text)"}}>{health.latest_signal_date}</strong>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Orders;