import BiomarkerCard from "./BiomarkerCard";
import ComparisonChart from "./ComparisonChart";

// Section 3: exploratory view — how diffusion-reconstructed cells (C) shift
// the result when blended into the combined biomarker (B).
export default function ReconstructionSection({ biomarker }) {
  return (
    <section className="card">
      <h2>3. Reconstruction (exploratory)</h2>
      <p className="section-intro">
        How diffusion-recovered cells change the result.
      </p>

      <div className="card-row">
        <BiomarkerCard
          title="Biomarker C — Reconstruction only"
          data={biomarker.C_reconstruction_only}
        />
        <BiomarkerCard
          title="Biomarker B — Combined"
          data={biomarker.B_combined}
        />
      </div>

      <ComparisonChart
        aValue={biomarker.A_real_only.abnormal_per_1000}
        bValue={biomarker.B_combined.abnormal_per_1000}
        cValue={biomarker.C_reconstruction_only.abnormal_per_1000}
      />
    </section>
  );
}
