"""
Detection stage — YOLO cell detector.

Loads the trained YOLOv8 weight and detects cells in an image, returning
bounding boxes. This is stage 1 of the real pipeline; classification and
reconstruction are added in later stages.

The model is loaded ONCE and reused (loading is slow; inference is fast).
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List
import io

from PIL import Image
import numpy as np


# path to the weight (kept out of git by .gitignore's *.pt rule)
WEIGHTS_PATH = Path(__file__).resolve().parent.parent / "models" / "yolo_cell_detector_best.pt"


@dataclass
class Detection:
    """One detected cell: box in pixel coords + confidence."""
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    def as_dict(self) -> dict:
        return {
            "x1": round(self.x1, 1), "y1": round(self.y1, 1),
            "x2": round(self.x2, 1), "y2": round(self.y2, 1),
            "conf": round(self.conf, 3),
        }


class CellDetector:
    """Wraps the YOLO model. Loads lazily on first use."""

    def __init__(self, weights_path: Path = WEIGHTS_PATH, conf: float = 0.25, imgsz: int = 1280):
        self.weights_path = Path(weights_path)
        self.conf = conf
        self.imgsz = imgsz
        self._model = None

    def _ensure_loaded(self):
        if self._model is None:
            if not self.weights_path.exists():
                raise FileNotFoundError(
                    f"YOLO weights not found at {self.weights_path}. "
                    "Place yolo_cell_detector_best.pt in backend/models/."
                )
            from ultralytics import YOLO  # imported here so the app starts even if ultralytics is heavy
            self._model = YOLO(str(self.weights_path))

    def detect(self, image: Image.Image) -> List[Detection]:
        """Run detection on a PIL image, return list of Detection boxes."""
        self._ensure_loaded()
        # ultralytics accepts a numpy array (RGB)
        arr = np.array(image.convert("RGB"))
        results = self._model.predict(arr, imgsz=self.imgsz, conf=self.conf, verbose=False)
        dets: List[Detection] = []
        for r in results:
            if r.boxes is None:
                continue
            for b in r.boxes:
                x1, y1, x2, y2 = [float(v) for v in b.xyxy[0].tolist()]
                conf = float(b.conf[0].item())
                dets.append(Detection(x1, y1, x2, y2, conf))
        return dets

    def detect_bytes(self, image_bytes: bytes) -> List[Detection]:
        img = Image.open(io.BytesIO(image_bytes))
        return self.detect(img)


# ---- standalone test: run detection on one image and report ----
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m pipeline.detector <path_to_image>")
        raise SystemExit(1)
    path = sys.argv[1]
    det = CellDetector()
    with open(path, "rb") as f:
        cells = det.detect_bytes(f.read())
    print(f"Detected {len(cells)} cells in {path}")
    for i, c in enumerate(cells[:10]):
        print(f"  cell {i+1}: box=({c.x1:.0f},{c.y1:.0f},{c.x2:.0f},{c.y2:.0f}) conf={c.conf:.2f}")
    if len(cells) > 10:
        print(f"  ... and {len(cells)-10} more")