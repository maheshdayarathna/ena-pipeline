import BreakdownTable from "./BreakdownTable";

// Section 4: raw per-source counts behind the biomarkers above.
// breakdown_by_source has one row per source ("single", "watershed_whole",
// "inpainted") — we split it into the two tables by source name.
export default function BreakdownSection({ biomarker }) {
  const bySource = Object.fromEntries(
    biomarker.breakdown_by_source.map((row) => [row.source, row])
  );
  const observedRows = ["single", "watershed_whole"]
    .map((key) => bySource[key])
    .filter(Boolean);
  const reconstructedRows = ["inpainted"]
    .map((key) => bySource[key])
    .filter(Boolean);

  return (
    <section className="card">
      <h2>4. Breakdown by source</h2>
      <div className="card-row">
        <BreakdownTable title="Observed cells (A)" rows={observedRows} />
        <BreakdownTable title="Reconstructed cells (C)" rows={reconstructedRows} />
      </div>
    </section>
  );
}
