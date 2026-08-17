import { formatPer1000 } from "../format";

// Simple bar chart comparing the three abnormal_per_1000 values.
// Hand-drawn with plain divs (bar height as a % of the largest value) rather
// than pulling in a charting library — there are only ever three bars, so a
// dependency isn't worth it.
export default function ComparisonChart({ aValue, bValue, cValue }) {
  const bars = [
    { key: "A", label: "A · observed", value: aValue },
    { key: "B", label: "B · combined", value: bValue },
    { key: "C", label: "C · reconstructed", value: cValue },
  ];
  const maxValue = Math.max(...bars.map((b) => b.value), 1);

  return (
    <div className="chart">
      <div className="chart-bars">
        {bars.map((bar) => (
          <div className="chart-bar-col" key={bar.key}>
            <div className="chart-bar-value">{formatPer1000(bar.value)}</div>
            <div
              className={`chart-bar chart-bar--${bar.key}`}
              style={{ height: `${(bar.value / maxValue) * 100}%` }}
            />
            <div className="chart-bar-label">{bar.label}</div>
          </div>
        ))}
      </div>
      <p className="chart-caption">
        Reconstruction (C) reads more abnormal, pulling B above A.
      </p>
    </div>
  );
}
