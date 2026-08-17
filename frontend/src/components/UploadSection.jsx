import { useEffect, useRef, useState } from "react";

// Key the diffusion toggle is persisted under, so it survives page refreshes
// and carries over between uploads.
const DIFFUSION_STORAGE_KEY = "ena-app:use-diffusion";

function loadStoredUseDiffusion() {
  try {
    return localStorage.getItem(DIFFUSION_STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

// Section 1: pick/drop one image, preview it, and trigger the analysis.
//
// This component only owns the "which file is selected + its preview URL"
// state. It knows nothing about the API call itself — it just calls the
// onAnalyze(file) prop that App.jsx passes in, and App.jsx owns the
// loading/result/error state that comes back from the network.
export default function UploadSection({ onAnalyze, loading, error }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [useDiffusion, setUseDiffusion] = useState(loadStoredUseDiffusion);
  const inputRef = useRef(null);

  useEffect(() => {
    try {
      localStorage.setItem(DIFFUSION_STORAGE_KEY, String(useDiffusion));
    } catch {
      // localStorage unavailable (e.g. private browsing) — toggle still
      // works for the current session, it just won't persist.
    }
  }, [useDiffusion]);

  // Build/revoke an object URL for the preview whenever the selected file changes.
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function handleFiles(fileList) {
    const picked = fileList && fileList[0];
    if (picked && picked.type.startsWith("image/")) {
      setFile(picked);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setIsDragOver(false);
    handleFiles(event.dataTransfer.files);
  }

  return (
    <section className="card">
      <h2>1. Upload a blood smear image</h2>

      <div
        className={`drop-zone ${isDragOver ? "drop-zone--active" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
      >
        {previewUrl ? (
          <div className="preview-wrap">
            {/* Future work: draw detected-cell bounding boxes/overlay on top
                of this preview image once the real pipeline exposes cell
                coordinates. For now it's just a plain <img>. */}
            <img src={previewUrl} alt="Selected smear preview" className="preview-img" />
          </div>
        ) : (
          <p>Drag and drop an image here, or click to choose a file.</p>
        )}
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <button
        className="btn-primary"
        disabled={!file || loading}
        onClick={() => onAnalyze(file, useDiffusion)}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>

      <div className="toggle-row">
        <button
          type="button"
          role="switch"
          aria-checked={useDiffusion}
          className={`toggle-switch ${useDiffusion ? "toggle-switch--on" : ""}`}
          onClick={() => setUseDiffusion((prev) => !prev)}
          disabled={loading}
        >
          <span className="toggle-switch-knob" />
        </button>
        <div className="toggle-text">
          <span className="toggle-label">Diffusion reconstruction</span>
          <span className="toggle-subtitle">Slow — several minutes on CPU · off by default</span>
        </div>
      </div>

      {loading && (
        <div className={`loading-note ${useDiffusion ? "loading-note--warning" : "loading-note--info"}`}>
          <div className="loading-bar-track" aria-hidden="true">
            <div className="loading-bar-fill" />
          </div>
          <p className="loading-text">
            {useDiffusion
              ? "Running full pipeline with diffusion reconstruction — this can take several minutes on CPU. Please wait."
              : "Analyzing image… (about 40 seconds)"}
          </p>
        </div>
      )}

      {error && <p className="error-text">{error}</p>}
    </section>
  );
}
