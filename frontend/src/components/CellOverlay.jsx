// SVG overlay drawn on top of the uploaded image preview, showing detected
// cell boxes from the /analyze response (meta.cells + meta.image_size).
//
// Scaling: the <svg> is absolutely positioned to exactly cover the rendered
// <img> (see the "preview-frame" wrapper in UploadSection), and its
// viewBox is set to the ORIGINAL image pixel size. The browser then scales
// the box coordinates from original pixels -> displayed pixels for us
// (displayedWidth/imageSize.width and displayedHeight/imageSize.height),
// and keeps them correct automatically on every resize/reflow — no resize
// listener needed.
//
// Green = normal, red = abnormal. Solid border = observed single cell.
// Dashed border = reconstructed (watershed_whole / inpainted). Some split
// cells intentionally share the same box (overlap is expected).
export default function CellOverlay({ cells, imageSize }) {
  if (!imageSize || !imageSize.width || !imageSize.height) return null;

  return (
    <svg
      className="cell-overlay"
      viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {cells.map((cell, i) => {
        const box = cell.box || {};
        const x = Number(box.x1) || 0;
        const y = Number(box.y1) || 0;
        const w = Math.max(Number(box.x2) - Number(box.x1), 0);
        const h = Math.max(Number(box.y2) - Number(box.y1), 0);
        const isAbnormal = cell.label === "abnormal";
        const isReconstructed = cell.source !== "single";

        return (
          <rect
            key={i}
            x={x}
            y={y}
            width={w}
            height={h}
            className={[
              "cell-box",
              isAbnormal ? "cell-box--abnormal" : "cell-box--normal",
              isReconstructed ? "cell-box--dashed" : "",
            ].join(" ")}
          />
        );
      })}
    </svg>
  );
}
