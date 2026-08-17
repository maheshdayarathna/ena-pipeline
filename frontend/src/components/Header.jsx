// Static top banner: project title + one-line subtitle. No props, no state.
export default function Header() {
  return (
    <header className="header">
      <h1>ENA Biomarker — Tilapia Blood Smear Analysis</h1>
      <p className="subtitle">
        Upload a blood smear image to compute the erythrocyte nuclear
        abnormality (ENA) biomarker.
      </p>
    </header>
  );
}
