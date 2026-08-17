import { formatCount, formatPer1000 } from "../format";

// Renders one biomarker view (A, B, or C — they're all the same shape).
// `variant="primary"` makes the card bigger with an accent border and a
// badge, used once for A in Section 2. The plain (default) variant is used
// for the smaller B/C cards in Section 3.
export default function BiomarkerCard({ title, badge, data, variant = "default" }) {
  const isPrimary = variant === "primary";

  return (
    <div className={`biomarker-card ${isPrimary ? "biomarker-card--primary" : ""}`}>
      {badge && <span className="badge">{badge}</span>}
      <h3>{title}</h3>

      <div className={isPrimary ? "hero-number" : "sub-number"}>
        {formatPer1000(data.abnormal_per_1000)}
      </div>
      <div className="hero-label">abnormal per 1,000 RBCs</div>

      <dl className="cell-counts">
        <div>
          <dt>Total cells</dt>
          <dd>{formatCount(data.total_cells)}</dd>
        </div>
        <div>
          <dt>Normal</dt>
          <dd>{formatCount(data.normal_cells)}</dd>
        </div>
        <div>
          <dt>Abnormal</dt>
          <dd>{formatCount(data.abnormal_cells)}</dd>
        </div>
      </dl>
    </div>
  );
}
