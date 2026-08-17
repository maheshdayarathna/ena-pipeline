"""
Real pipeline (stages 1+2): detection -> classification.

Implements the same Pipeline interface as the mock, so it drops into the
/analyze endpoint with a one-line swap. For now EVERY detected box is treated
as a single observed cell (source = SINGLE). Multi-cell watershed + diffusion
reconstruction is added in stage 3; until then reconstruction count C = 0 and
biomarker A == B, which is correct and honest for this stage.

Also returns per-cell box + label in meta, so the frontend overlay can draw
coloured boxes later.
"""

from __future__ import annotations
import io
from PIL import Image

from core.biomarker import Cell, CellSource, ABNORMAL, NORMAL
from pipeline.base import Pipeline, PipelineResult
from pipeline.detector import CellDetector
from pipeline.classifier import CellClassifier


class RealPipeline(Pipeline):
    def __init__(self, det_conf: float = 0.25):
        self.detector = CellDetector(conf=det_conf)
        self.classifier = CellClassifier()

    def analyze(self, image_bytes: bytes, filename: str = "") -> PipelineResult:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # stage 1: detect
        detections = self.detector.detect(image)

        # stage 2: classify each detected box (all treated as SINGLE for now)
        labels = self.classifier.classify_boxes(image, detections)

        cells = []
        cell_records = []   # for the overlay: box + label + source
        for det, (label, p_abn) in zip(detections, labels):
            cells.append(Cell(CellSource.SINGLE, label))
            cell_records.append({
                "box": det.as_dict(),
                "source": CellSource.SINGLE.value,
                "label": label,
                "p_abnormal": round(p_abn, 3),
                "det_conf": round(det.conf, 3),
            })

        n_abn = sum(1 for _, (lab, _) in zip(detections, labels) if lab == ABNORMAL)
        meta = {
            "pipeline": self.name,
            "note": "REAL models: YOLO detection + DenseNet classification. "
                    "Reconstruction (stage 3) not yet added, so all cells are 'single'.",
            "image_filename": filename,
            "image_size": {"width": image.width, "height": image.height},
            "stage_counts": {
                "detected": len(detections),
                "classified_abnormal": n_abn,
                "classified_normal": len(detections) - n_abn,
                "watershed_whole": 0,
                "inpainted": 0,
            },
            "cells": cell_records,   # box + label + source, for the overlay
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

    print("Running detection + classification (first run loads models, ~slow)...")
    pipe = RealPipeline()
    result = pipe.analyze(img_bytes, filename=sys.argv[1])
    bm = compute_biomarker(result.cells)

    sc = result.meta["stage_counts"]
    print(f"\nDetected cells      : {sc['detected']}")
    print(f"  classified normal : {sc['classified_normal']}")
    print(f"  classified abnormal: {sc['classified_abnormal']}")
    print("\n--- Biomarker (real detection + classification) ---")
    d = bm.as_dict()["biomarkers"]
    a = d["A_real_only"]
    print(f"A real-only : {a['abnormal_cells']}/{a['total_cells']} abnormal "
          f"= {a['abnormal_per_1000']} per 1000")
    print("\n(Reconstruction not added yet, so B == A and C == 0.)")