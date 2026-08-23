import { formatCount, formatDateTime, formatPer1000 } from "../format";
import { API_BASE } from "../api";

// Bottom-of-page section: table of past analyses fetched from GET /history.
// App.jsx owns the fetching (on load + after each new analysis) and passes
// down rows/loading/error plus a refresh callback for the manual button.
// The backend already returns newest-first (ORDER BY id DESC).
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
        <div className="table-scroll">
          <table className="history-table">
            <thead>
              <tr>
                <th rowSpan={2}>Date / time</th>
                <th rowSpan={2}>Filename</th>
                <th rowSpan={2}>Diffusion</th>
                <th colSpan={3} className="col-group col-group--primary">
                  Biomarker A (primary)
                </th>
                <th colSpan={3} className="col-group">
                  Biomarker B
                </th>
                <th colSpan={3} className="col-group">
                  Biomarker C
                </th>
                <th rowSpan={2}>Report</th>
              </tr>
              <tr>
                <th className="col-primary">Total</th>
                <th className="col-primary">Abnormal</th>
                <th className="col-primary">/ 1000</th>
                <th>Total</th>
                <th>Abnormal</th>
                <th>/ 1000</th>
                <th>Total</th>
                <th>Abnormal</th>
                <th>/ 1000</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((row) => (
                <tr key={row.id}>
                  <td>{formatDateTime(row.created_at)}</td>
                  <td>{row.filename || "-"}</td>
                  <td>{row.use_diffusion ? "Yes" : "No"}</td>
                  <td className="col-primary">{formatCount(row.a_total)}</td>
                  <td className="col-primary">{formatCount(row.a_abnormal)}</td>
                  <td className="col-primary">{formatPer1000(row.a_per_1000)}</td>
                  <td>{formatCount(row.b_total)}</td>
                  <td>{formatCount(row.b_abnormal)}</td>
                  <td>{formatPer1000(row.b_per_1000)}</td>
                  <td>{formatCount(row.c_total)}</td>
                  <td>{formatCount(row.c_abnormal)}</td>
                  <td>{formatPer1000(row.c_per_1000)}</td>
                  <td>
                    <a
                      className="btn-secondary btn-table"
                      href={`${API_BASE}/report/${row.id}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Download PDF
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
