"""
Watershed splitter — multi-cell detection + splitting.

Each detected crop is passed through watershed. This serves DUAL duty:
  - DETECT multi-cell: if watershed finds >1 cell-sized region, the crop held
    multiple overlapping cells.
  - SPLIT: return each region as a separate cell.

Regions are classified as WHOLE (fully inside the crop -> observed, counts to A)
or CLIPPED (touching the crop edge -> will go to diffusion inpainting later).

This mirrors the reconstruction investigation's watershed method, so the live
app is consistent with the documented approach. Honest limitation: watershed
here both detects and splits, so its over-splitting tendency (~69% count
recovery in validation) affects both roles.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
from enum import Enum

import numpy as np
import cv2
from scipy import ndimage as ndi
from skimage.feature import peak_local_max
from skimage.segmentation import watershed
from PIL import Image


MIN_CELL_AREA = 800        # regions smaller than this are debris -> discarded
MIN_DISTANCE_FRAC = 0.22   # peak spacing, from the validated watershed config


class RegionKind(str, Enum):
    WHOLE = "whole"        # fully inside crop -> observed
    CLIPPED = "clipped"    # touches crop edge -> needs inpainting
    FRAGMENT = "fragment"  # too small -> discard


@dataclass
class Region:
    kind: RegionKind
    crop: Image.Image           # the region's pixels on a canvas (for classify/inpaint)
    area: int


def _segment(bgr: np.ndarray) -> np.ndarray:
    """Watershed label map for a crop (BGR numpy)."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, fg = cv2.threshold(255 - gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=2)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=2)
    mask = fg > 0
    if mask.sum() < MIN_CELL_AREA:
        return np.zeros(gray.shape, dtype=int)
    dist = ndi.distance_transform_edt(mask)
    md = max(8, int(min(gray.shape) * MIN_DISTANCE_FRAC))
    coords = peak_local_max(dist, min_distance=md, labels=mask, exclude_border=False)
    if len(coords) == 0:
        return mask.astype(int)
    markers = np.zeros(dist.shape, dtype=int)
    for i, (y, x) in enumerate(coords, start=1):
        markers[y, x] = i
    return watershed(-dist, markers, mask=mask)


def _touches_edge(region_mask: np.ndarray) -> bool:
    return bool(region_mask[0, :].any() or region_mask[-1, :].any() or
                region_mask[:, 0].any() or region_mask[:, -1].any())


def split_crop(crop_rgb: Image.Image) -> List[Region]:
    """
    Segment a crop and return its regions (whole / clipped / fragment).
    If watershed yields exactly one whole region, the crop was a single cell.
    """
    rgb = np.array(crop_rgb.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    labels = _segment(bgr)

    regions: List[Region] = []
    n = int(labels.max())
    for lab in range(1, n + 1):
        rm = labels == lab
        area = int(rm.sum())
        if area < MIN_CELL_AREA:
            regions.append(Region(RegionKind.FRAGMENT, crop_rgb, area))
            continue
        # bounding box of the region
        ys, xs = np.where(rm)
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        region_img = Image.fromarray(rgb[y0:y1 + 1, x0:x1 + 1])
        kind = RegionKind.CLIPPED if _touches_edge(rm) else RegionKind.WHOLE
        regions.append(Region(kind, region_img, area))
    return regions


def is_multicell(regions: List[Region]) -> bool:
    """A crop is multi-cell if it yields >1 non-fragment region."""
    real = [r for r in regions if r.kind != RegionKind.FRAGMENT]
    return len(real) > 1