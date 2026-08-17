import BiomarkerCard from "./BiomarkerCard";

// Section 2: the main outcome — biomarker A (real cells only), marked PRIMARY.
export default function PrimarySection({ biomarker }) {
  return (
    <section className="card">
      <h2>2. Main outcome</h2>
      <BiomarkerCard
        title="Biomarker A — Observed cells only"
        badge="primary · observed cells"
        data={biomarker.A_real_only}
        variant="primary"
      />
    </section>
  );
}
