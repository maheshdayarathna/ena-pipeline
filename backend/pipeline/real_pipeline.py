"""
Real pipeline: detection -> watershed split -> (diffusion inpaint) -> classification.

Full pipeline as specified:
  1. YOLO detects cells -> boxes.
  2. Each crop -> watershed:
       1 region  -> single observed cell (source = SINGLE) -> biomarker A
       >1 region -> multi-cell:
            whole regions   -> source = WATERSHED_WHOLE (reconstruction layer C)
            clipped regions -> diffusion inpaint -> source = INPAINTED (layer C)
  3. Classify each resulting cell.

Biomarker A (primary) = single cells only. Watershed_whole + inpainted form the
exploratory reconstruction layer (C). This keeps the primary biomarker on the
validated detection->classification path; reconstruction (documented as
unreliable) is reported separately.

Diffusion inpainting is capped + reduced-steps for CPU demo feasibility (see
inpainter.py); the meta flags it as an approximate sample.
"""

from __future__ import annotations
import io
from PIL import Image

from core.biomarker import Cell, CellSource, ABNORMAL, NORMAL
from pipeline.base import Pipeline, PipelineResult
from pipeline.detector import CellDetector
from pipeline.classifier import CellClassifier
from pipeline.watershed_split import split_crop, is_multicell, RegionKind
from pipeline.inpainter import DiffusionInpainter


class RealPipeline(Pipeline):
    def __init__(self, det_conf: float = 0.25):
        self.detector = CellDetector(conf=det_conf)
        self.classifier = CellClassifier()
        self._inpainter = None   # loaded lazily only when diffusion is requested

    def _get_inpainter(self):
        if self._inpainter is None:
            self._inpainter = DiffusionInpainter()
        return self._inpainter

    def analyze(self, image_bytes: bytes, filename: str = "", use_diffusion: bool = False) -> PipelineResult:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        detections = self.detector.detect(image)

        # collect cells by source
        single_crops = []      # (crop, det)
        whole_crops = []       # (crop, det)
        clipped_crops = []     # (crop, det)
        n_fragment = 0

        for det in detections:
            crop = image.crop((int(det.x1), int(det.y1), int(det.x2), int(det.y2)))
            if crop.width < 4 or crop.height < 4:
                continue
            regions = split_crop(crop)
            if not is_multicell(regions):
                single_crops.append((crop, det))
            else:
                for r in regions:
                    if r.kind == RegionKind.WHOLE:
                        whole_crops.append((r.crop, det))
                    elif r.kind == RegionKind.CLIPPED:
                        clipped_crops.append((r.crop, det))
                    else:
                        n_fragment += 1

        # diffusion inpaint the clipped crops (only if requested)
        inpaint_info = {"clipped_total": len(clipped_crops), "inpainted": 0,
                        "enabled": use_diffusion}
        inpainted_imgs = []
        if use_diffusion and clipped_crops:
            imgs, info = self._get_inpainter().inpaint_clipped([c for c, _ in clipped_crops])
            inpaint_info = {**info, "enabled": True}
            inpainted_imgs = imgs
        # clipped crops beyond the cap are NOT counted (honest: we only count what we inpainted)
        inpainted_pairs = list(zip(inpainted_imgs, [d for _, d in clipped_crops]))

        # assemble (crop, source, det) for classification
        items = (
            [(c, CellSource.SINGLE, d) for c, d in single_crops] +
            [(c, CellSource.WATERSHED_WHOLE, d) for c, d in whole_crops] +
            [(c, CellSource.INPAINTED, d) for c, d in inpainted_pairs]
        )

        cells = []
        cell_records = []
        for crop, source, det in items:
            label, p_abn = self.classifier.classify_crop(crop)
            cells.append(Cell(source, label))
            cell_records.append({
                "box": det.as_dict(),
                "source": source.value,
                "label": label,
                "p_abnormal": round(p_abn, 3),
            })

        n_abn = sum(1 for c in cells if c.label == ABNORMAL)
        meta = {
            "pipeline": self.name,
            "note": "REAL full pipeline: YOLO + watershed + diffusion inpainting + DenseNet. "
                    "Biomarker A = single cells (primary). Watershed + inpainted = "
                    "exploratory reconstruction (C).",
            "image_filename": filename,
            "image_size": {"width": image.width, "height": image.height},
            "diffusion": inpaint_info,
            "stage_counts": {
                "detected_boxes": len(detections),
                "single_cells": len(single_crops),
                "watershed_whole": len(whole_crops),
                "clipped_found": len(clipped_crops),
                "inpainted": len(inpainted_pairs),
                "fragments_discarded": n_fragment,
                "classified_abnormal": n_abn,
                "classified_normal": len(cells) - n_abn,
            },
            "cells": cell_records,
        }
        return PipelineResult(cells=cells, meta=meta)


if __name__ == "__main__":
    import sys, time
    from core.biomarker import compute_biomarker
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.real_pipeline <path_to_image>")
        raise SystemExit(1)
    with open(sys.argv[1], "rb") as f:
        img_bytes = f.read()
    print("Running FULL pipeline (detection + watershed + diffusion + classification)...")
    t0 = time.time()
    pipe = RealPipeline()
    result = pipe.analyze(img_bytes, filename=sys.argv[1], use_diffusion=True)
    bm = compute_biomarker(result.cells)
    sc = result.meta["stage_counts"]
    print(f"\nTook {time.time()-t0:.0f}s")
    print(f"Detected boxes    : {sc['detected_boxes']}")
    print(f"  single (A)      : {sc['single_cells']}")
    print(f"  watershed whole : {sc['watershed_whole']}")
    print(f"  clipped found   : {sc['clipped_found']}")
    print(f"  inpainted (capped): {sc['inpainted']}")
    print(f"  fragments       : {sc['fragments_discarded']}")
    d = bm.as_dict()["biomarkers"]
    print(f"\nA (primary, single) : {d['A_real_only']['abnormal_per_1000']} per 1000")
    print(f"B (combined)        : {d['B_combined']['abnormal_per_1000']} per 1000")
    print(f"C (reconstruction)  : {d['C_reconstruction_only']['abnormal_per_1000']} per 1000")
    print(f"\ndiffusion: {result.meta['diffusion'].get('note','')}")