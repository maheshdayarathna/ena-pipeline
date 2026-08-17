import { formatCount } from "../format";

// One small table of source-level counts (total/normal/abnormal per row).
// `rows` is a filtered slice of biomarker.breakdown_by_source.
export default function BreakdownTable({ title, rows }) {
  return (
    <div className="breakdown-table">
      <h4>{title}</h4>
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Total</th>
            <th>Normal</th>
            <th>Abnormal</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.source}>
              <td>{row.source}</td>
              <td>{formatCount(row.total)}</td>
              <td>{formatCount(row.normal)}</td>
              <td>{formatCount(row.abnormal)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
