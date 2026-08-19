import { formatDateTime, formatPer1000 } from "../format";

// Bottom-of-page section: table of past analyses fetched from GET /history.
// App.jsx owns the fetching (on load + after each new analysis) and passes
// down rows/loading/error plus a refresh callback for the manual button.
export default function HistorySection({ analyses, loading, error, onRefresh }) {
  return (
    <section className="card">
      <div className="history-header">
        <h2>Analysis history</h2>
        <button className="btn-secondary" onClick={onRefresh} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {!error && analyses.length === 0 && (
        <p className="section-intro">No analyses yet.</p>
      )}

      {!error && analyses.length > 0 && (
        <table className="history-table">
          <thead>
            <tr>
              <th>Date / time</th>
              <th>Filename</th>
              <th>Diffusion</th>
              <th>A / 1000</th>
              <th>B / 1000</th>
              <th>C / 1000</th>
            </tr>
          </thead>
          <tbody>
            {analyses.map((row) => (
              <tr key={row.id}>
                <td>{formatDateTime(row.created_at)}</td>
                <td>{row.filename || "-"}</td>
                <td>{row.use_diffusion ? "Yes" : "No"}</td>
                <td>{formatPer1000(row.a_per_1000)}</td>
                <td>{formatPer1000(row.b_per_1000)}</td>
                <td>{formatPer1000(row.c_per_1000)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
