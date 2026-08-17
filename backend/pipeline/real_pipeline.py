"""
Real pipeline: detection -> watershed split -> classification.

Stages now live:
  1. YOLO detects cells -> boxes.
  2. Each crop -> watershed:
       - 1 region  -> single observed cell (source = SINGLE)
       - >1 region -> multi-cell:
            whole regions   -> classified (source = WATERSHED_WHOLE, counts to A)
            clipped regions -> counted conservatively for now (diffusion next stage)
  3. Classify each resulting cell (batched).

Reconstruction (diffusion inpainting of clipped regions) is the NEXT stage;
until then clipped regions are tagged and reported but not inpainted.
"""

from __future__ import annotations
import io
from PIL import Image

from core.biomarker import Cell, CellSource, ABNORMAL, NORMAL
from pipeline.base import Pipeline, PipelineResult
from pipeline.detector import CellDetector
from pipeline.classifier import CellClassifier
from pipeline.watershed_split import split_crop, is_multicell, RegionKind


class RealPipeline(Pipeline):
    def __init__(self, det_conf: float = 0.25):
        self.detector = CellDetector(conf=det_conf)
        self.classifier = CellClassifier()

    def analyze(self, image_bytes: bytes, filename: str = "") -> PipelineResult:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # stage 1: detect
        detections = self.detector.detect(image)

        # stage 2: watershed each crop -> collect classifiable regions
        # each entry: (pil_crop, source, box_for_overlay)
        to_classify = []
        n_single = n_whole = n_clipped = n_fragment = 0

        for det in detections:
            crop = image.crop((int(det.x1), int(det.y1), int(det.x2), int(det.y2)))
            if crop.width < 4 or crop.height < 4:
                continue
            regions = split_crop(crop)

            if not is_multicell(regions):
                # single cell — classify the original crop
                to_classify.append((crop, CellSource.SINGLE, det))
                n_single += 1
            else:
                for r in regions:
                    if r.kind == RegionKind.WHOLE:
                        to_classify.append((r.crop, CellSource.WATERSHED_WHOLE, det))
                        n_whole += 1
                    elif r.kind == RegionKind.CLIPPED:
                        # NEXT STAGE: diffusion inpaint. For now, count conservatively
                        # as an observed whole cell so it is not lost. Tagged separately
                        # in stage counts so we can see how many await inpainting.
                        to_classify.append((r.crop, CellSource.WATERSHED_WHOLE, det))
                        n_clipped += 1
                    else:
                        n_fragment += 1

        # stage 3: classify everything (batched). Build a lightweight box list.
        class _B:
            __slots__ = ("x1", "y1", "x2", "y2")
            def __init__(s, c): s.x1, s.y1, s.x2, s.y2 = 0, 0, c.width, c.height

        cells = []
        cell_records = []
        # classify per-crop (each crop is its own image here); batch within the classifier
        crops = [c for (c, _src, _d) in to_classify]
        # classify each crop image as a whole (box = full crop)
        results = []
        for c in crops:
            label, p = self.classifier.classify_crop(c)
            results.append((label, p))

        for (crop, source, det), (label, p_abn) in zip(to_classify, results):
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
            "note": "REAL models: YOLO + watershed split + DenseNet. Diffusion "
                    "inpainting (for clipped cells) is the next stage; clipped "
                    "regions are currently counted as observed.",
            "image_filename": filename,
            "image_size": {"width": image.width, "height": image.height},
            "stage_counts": {
                "detected_boxes": len(detections),
                "single_cells": n_single,
                "watershed_whole": n_whole,
                "clipped_awaiting_inpaint": n_clipped,
                "fragments_discarded": n_fragment,
                "classified_abnormal": n_abn,
                "classified_normal": len(cells) - n_abn,
                "inpainted": 0,
            },
            "cells": cell_records,
        }
        return PipelineResult(cells=cells, meta=meta)


if __name__ == "__main__":
    import sys
    from core.biomarker import compute_biomarker
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.real_pipeline <path_to_image>")
        raise SystemExit(1)
    with open(sys.argv[1], "rb") as f:
        img_bytes = f.read()
    print("Running detection + watershed + classification (first run loads models)...")
    pipe = RealPipeline()
    result = pipe.analyze(img_bytes, filename=sys.argv[1])
    bm = compute_biomarker(result.cells)
    sc = result.meta["stage_counts"]
    print(f"\nDetected boxes         : {sc['detected_boxes']}")
    print(f"  single cells         : {sc['single_cells']}")
    print(f"  watershed whole      : {sc['watershed_whole']}")
    print(f"  clipped (await inpaint): {sc['clipped_awaiting_inpaint']}")
    print(f"  fragments discarded  : {sc['fragments_discarded']}")
    print(f"  total classified     : {sc['classified_normal'] + sc['classified_abnormal']}")
    d = bm.as_dict()["biomarkers"]
    a = d["A_real_only"]
    print(f"\nA real-only: {a['abnormal_cells']}/{a['total_cells']} = {a['abnormal_per_1000']} per 1000")