import { useEffect, useRef, useState } from "react";

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
  const inputRef = useRef(null);

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
        onClick={() => onAnalyze(file)}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>

      {error && <p className="error-text">{error}</p>}
    </section>
  );
}
