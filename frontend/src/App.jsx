import { useEffect, useState } from "react";
import { analyzeImage, fetchHistory } from "./api";
import Header from "./components/Header";
import SyntheticBanner from "./components/SyntheticBanner";
import UploadSection from "./components/UploadSection";
import PrimarySection from "./components/PrimarySection";
import ReconstructionSection from "./components/ReconstructionSection";
import BreakdownSection from "./components/BreakdownSection";
import HistorySection from "./components/HistorySection";

// Top-level component: owns all state for the single-page flow.
//   result === null  -> only Header + Upload are shown
//   loading === true -> Upload shows a loading indicator
//   result !== null  -> Sections 2-4 render from result.biomarker / result.meta
//   error            -> shown inside UploadSection, user can retry
export default function App() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);

  async function loadHistory() {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      setHistory(await fetchHistory());
    } catch (err) {
      setHistoryError(err.message);
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  async function handleAnalyze(file, useDiffusion) {
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeImage(file, useDiffusion);
      setResult(data);
      loadHistory();
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

        <HistorySection
          analyses={history}
          loading={historyLoading}
          error={historyError}
          onRefresh={loadHistory}
        />
      </main>
    </div>
  );
}
