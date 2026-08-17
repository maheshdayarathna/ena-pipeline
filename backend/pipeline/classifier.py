"""
Classification stage — DenseNet121 binary classifier (normal vs abnormal).

For each detected cell box, crop that region and classify it. The classifier
outputs 2 logits; which index means "abnormal" is set by ABNORMAL_INDEX below.

IMPORTANT: ABNORMAL_INDEX must match how the model was TRAINED. We do not
assume it — verify_labels() checks it against known-label crops. If known
abnormal cells come out "normal", flip ABNORMAL_INDEX (0 <-> 1).
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
import io

import numpy as np
from PIL import Image
import torch
import torch.nn as nn
from torchvision import models, transforms

WEIGHTS_PATH = Path(__file__).resolve().parent.parent / "models" / "densenet121_binary_final.pt"

# >>> The one setting that must match training. Verify with verify_labels(). <<<
# Common case: training built labels alphabetically ("abnormal","normal") -> abnormal=0.
# But if labels were assigned as (NC=0 normal, else=1) -> abnormal=1.
# DO NOT trust this default — run verify_labels() before believing any output.
ABNORMAL_INDEX = 1

NORMAL = "normal"
ABNORMAL = "abnormal"


class CellClassifier:
    def __init__(self, weights_path: Path = WEIGHTS_PATH, abnormal_index: int = ABNORMAL_INDEX):
        self.weights_path = Path(weights_path)
        self.abnormal_index = abnormal_index
        self._model = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._tf = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def _ensure_loaded(self):
        if self._model is None:
            if not self.weights_path.exists():
                raise FileNotFoundError(
                    f"Classifier weights not found at {self.weights_path}. "
                    "Place densenet121_binary_final.pt in backend/models/."
                )
            m = models.densenet121(weights=None)
            m.classifier = nn.Linear(m.classifier.in_features, 2)
            ck = torch.load(self.weights_path, map_location=self._device)
            state = ck["state_dict"] if isinstance(ck, dict) and "state_dict" in ck else ck
            m.load_state_dict(state)
            m.to(self._device).eval()
            self._model = m

    @torch.no_grad()
    def classify_crop(self, crop: Image.Image) -> Tuple[str, float]:
        """Return (label, p_abnormal) for one cell crop."""
        self._ensure_loaded()
        x = self._tf(crop.convert("RGB")).unsqueeze(0).to(self._device)
        probs = self._model(x).softmax(1)[0]
        p_abnormal = float(probs[self.abnormal_index].item())
        label = ABNORMAL if p_abnormal >= 0.5 else NORMAL
        return label, p_abnormal

    @torch.no_grad()
    def classify_boxes(self, image: Image.Image, boxes, batch_size: int = 32) -> List[Tuple[str, float]]:
        """
        Crop each box and classify in BATCHES (much faster on CPU than one at a
        time). boxes: objects with x1,y1,x2,y2. Returns (label, p_abnormal) per box.
        """
        self._ensure_loaded()
        image = image.convert("RGB")

        # crop all boxes first; remember which are too-small (skipped)
        tensors = []
        valid_idx = []
        results: List[Tuple[str, float]] = [(NORMAL, 0.0)] * len(boxes)
        for i, b in enumerate(boxes):
            crop = image.crop((int(b.x1), int(b.y1), int(b.x2), int(b.y2)))
            if crop.width < 2 or crop.height < 2:
                continue
            tensors.append(self._tf(crop))
            valid_idx.append(i)

        # run the classifier in batches
        for start in range(0, len(tensors), batch_size):
            batch = torch.stack(tensors[start:start + batch_size]).to(self._device)
            probs = self._model(batch).softmax(1)          # (B, 2)
            p_abn = probs[:, self.abnormal_index]           # (B,)
            for j, p in enumerate(p_abn.tolist()):
                idx = valid_idx[start + j]
                label = ABNORMAL if p >= 0.5 else NORMAL
                results[idx] = (label, float(p))
        return results


# ------------------------------------------------------------------
# VERIFICATION — run known-label crops through the classifier to confirm
# ABNORMAL_INDEX is correct. Point it at some crops you KNOW the label of.
# ------------------------------------------------------------------
def verify_labels(normal_crop_paths: List[str], abnormal_crop_paths: List[str],
                  abnormal_index: int = ABNORMAL_INDEX):
    """
    Classify known-normal and known-abnormal crops and report whether the
    current ABNORMAL_INDEX reads them correctly.
    """
    clf = CellClassifier(abnormal_index=abnormal_index)
    print(f"Testing with ABNORMAL_INDEX = {abnormal_index}\n")

    def run(paths, expected):
        correct = 0
        for p in paths:
            img = Image.open(p)
            label, p_abn = clf.classify_crop(img)
            ok = (label == expected)
            correct += ok
            print(f"  {Path(p).name}: predicted={label} (p_abn={p_abn:.2f}) expected={expected} {'OK' if ok else 'WRONG'}")
        return correct

    print("Known-NORMAL crops:")
    n_ok = run(normal_crop_paths, NORMAL)
    print("\nKnown-ABNORMAL crops:")
    a_ok = run(abnormal_crop_paths, ABNORMAL)

    total = len(normal_crop_paths) + len(abnormal_crop_paths)
    correct = n_ok + a_ok
    print(f"\nResult: {correct}/{total} correct.")
    if correct >= total * 0.6:
        print(f"-> ABNORMAL_INDEX = {abnormal_index} looks CORRECT.")
    else:
        print(f"-> Most predictions are WRONG. FLIP it: set ABNORMAL_INDEX = {1 - abnormal_index}.")


if __name__ == "__main__":
    # Example: fill in a few known crop paths, then run:
    #   python -m pipeline.classifier
    import sys
    print("To verify labels, edit this block with known crop paths, or call "
          "verify_labels([...normal...], [...abnormal...]) from a script.")