// Amber notice shown while the backend is running the mock pipeline.
// The backend flags this itself via meta.note, so this component just checks
// for the word "SYNTHETIC" — once real models are wired in, the backend note
// changes and this banner disappears automatically, no frontend change needed.
export default function SyntheticBanner({ note }) {
  if (!note || !note.includes("SYNTHETIC")) return null;

  return (
    <div className="synthetic-banner">
      Development mode: results use synthetic data (no models loaded yet).
    </div>
  );
}
