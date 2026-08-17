import { useState } from "react";
import { analyzeImage } from "./api";
import Header from "./components/Header";
import SyntheticBanner from "./components/SyntheticBanner";
import UploadSection from "./components/UploadSection";
import PrimarySection from "./components/PrimarySection";
import ReconstructionSection from "./components/ReconstructionSection";
import BreakdownSection from "./components/BreakdownSection";

// Top-level component: owns all state for the single-page flow.
//   result === null  -> only Header + Upload are shown
//   loading === true -> Upload shows a loading indicator
//   result !== null  -> Sections 2-4 render from result.biomarker / result.meta
//   error            -> shown inside UploadSection, user can retry
export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleAnalyze(file) {
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeImage(file);
      setResult(data);
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <Header />
      {result && <SyntheticBanner note={result.meta.note} />}

      <main>
        <UploadSection onAnalyze={handleAnalyze} loading={loading} error={error} />

        {result && (
          <>
            <PrimarySection biomarker={result.biomarker} />
            <ReconstructionSection biomarker={result.biomarker} />
            <BreakdownSection biomarker={result.biomarker} />
          </>
        )}
      </main>
    </div>
  );
}
