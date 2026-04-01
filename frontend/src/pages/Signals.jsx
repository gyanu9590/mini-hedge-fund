import { useApi } from "../hooks/useApi";
import { getSignalsToday } from "../api";

export default function Signals() {
  const { data, loading, error, refresh } = useApi(getSignalsToday, [], 60000);

  return (
    <div>
      <div className="page-title">
        Today's Signals
        <div className="page-sub">ML model — top 5 ranked by probability</div>
      </div>

      {loading && <div className="loading">Loading signals…</div>}
      {error   && <div className="error">{error}</div>}

      {data && (
        <>
          <div style={{ marginBottom: 14, display: "flex", gap: 12, alignItems: "center" }}>
            <span style={{ color: "var(--muted)", fontSize: 12 }}>
              Signal date: <strong style={{ color: "var(--text)" }}>
                {data[0]?.date ? String(data[0].date).split("T")[0] : "—"}
              </strong>
            </span>
            <button className="btn" style={{ fontSize: 11, padding: "5px 12px" }} onClick={refresh}>Refresh</button>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Signal</th>
                  <th>Probability</th>
                  <th>Strength</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600 }}>{row.symbol}</td>
                    <td>
                      {row.signal === 1
                        ? <span className="badge badge-buy">BUY</span>
                        : row.signal === -1
                        ? <span className="badge badge-sell">SELL</span>
                        : <span className="badge badge-hold">HOLD</span>
                      }
                    </td>
                    <td>{row.probability != null ? (row.probability * 100).toFixed(1) + "%" : "—"}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{
                          height: 6, borderRadius: 3,
                          width: Math.round((row.probability || 0) * 120),
                          background: row.signal === 1 ? "var(--green)" : row.signal === -1 ? "var(--red)" : "var(--border)",
                          minWidth: 4,
                        }} />
                        <span style={{ color: "var(--muted)", fontSize: 11 }}>
                          {row.probability > 0.7 ? "Strong" : row.probability > 0.5 ? "Moderate" : "Weak"}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}