// Legend for CellOverlay: explains outline color (normal/abnormal) and
// border style (observed/reconstructed) shown on the image overlay.
export default function CellOverlayLegend() {
  return (
    <ul className="cell-legend">
      <li>
        <span className="legend-swatch legend-swatch--normal" /> Normal
      </li>
      <li>
        <span className="legend-swatch legend-swatch--abnormal" /> Abnormal
      </li>
      <li>
        <span className="legend-swatch legend-swatch--solid" /> Observed (single cell)
      </li>
      <li>
        <span className="legend-swatch legend-swatch--dashed" /> Reconstructed (split / inpainted)
      </li>
    </ul>
  );
}
