import { useEffect, useState } from "react";
import { analyzeImage, fetchHistory, API_BASE } from "./api";
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
  // The exact File object the current `result` was computed from — lets
  // UploadSection know whether its preview still matches the analyzed
  // image (and so whether the cell overlay boxes are still valid).
  const [analyzedFile, setAnalyzedFile] = useState(null);

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
      setAnalyzedFile(file);
      loadHistory();
    } catch (err) {
      setError(err.message);
      setResult(null);
      setAnalyzedFile(null);
    } finally {
      setLoading(false);
    }
  }

  // Only set if the backend's /analyze response ever starts returning the
  // saved row's id (it doesn't today — the id is assigned by /history's
  // storage layer after the response is built). When absent, there's simply
  // no post-analysis download button; the same report is still reachable
  // from the history table below once it refreshes.
  const analyzedId = result?.id ?? result?.analysis_id ?? null;

  return (
    <div className="page">
      <Header />
      {result && <SyntheticBanner note={result.meta.note} />}

      <main>
        <UploadSection
          onAnalyze={handleAnalyze}
          loading={loading}
          error={error}
          resultMeta={result?.meta ?? null}
          analyzedFile={analyzedFile}
        />

        {result && (
          <>
            <PrimarySection biomarker={result.biomarker} />
            <ReconstructionSection biomarker={result.biomarker} />
            <BreakdownSection biomarker={result.biomarker} />
            {analyzedId != null && (
              <p className="report-download-row">
                <a
                  className="btn-secondary"
                  href={`${API_BASE}/report/${analyzedId}`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download report (PDF)
                </a>
              </p>
            )}
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
