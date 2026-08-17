"""
ENA biomarker counting core.

Implements the frozen three-way biomarker for the tilapia erythrocyte
nuclear-abnormality (ENA) pipeline:

    A  real-only        : observed cells only  (single + watershed-whole)   [PRIMARY]
    B  combined         : A + reconstructed (diffusion-inpainted) cells
    C  reconstruction-only : reconstructed cells alone                       [EXPLORATORY]

Each cell entering the counter carries:
  - source : how the cell was obtained (see CellSource)
  - label  : the classifier's call ("normal" / "abnormal")

The biomarker is abnormal nuclei per 1000 RBCs.

This module is pure logic: no I/O, no model calls. It is unit-tested in
tests/test_biomarker.py. Keeping it separate and tested means every number the
application shows is traceable to verified counting logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class CellSource(str, Enum):
    """How a classified cell was obtained from the image."""
    SINGLE = "single"                 # detected directly as a single-cell crop
    WATERSHED_WHOLE = "watershed_whole"  # whole cell recovered by watershed from a multi-cell crop
    INPAINTED = "inpainted"           # clipped cell completed by diffusion inpainting

    @property
    def is_primary(self) -> bool:
        """
        Primary (biomarker A) = cells detected directly as clean single cells.
        This is the validated detection->classification path. Watershed-split
        and inpainted cells are products of the reconstruction pipeline
        (documented as unreliable) and are therefore NOT part of the primary
        biomarker — they form the exploratory reconstruction layer.
        """
        return self is CellSource.SINGLE

    @property
    def is_reconstruction(self) -> bool:
        """
        Reconstruction layer (biomarker C) = anything produced by the multi-cell
        reconstruction process: watershed-split whole cells AND diffusion-inpainted
        cells. Reported separately as exploratory, never in the primary biomarker.
        """
        return self in (CellSource.WATERSHED_WHOLE, CellSource.INPAINTED)

    # kept for clarity: whether the pixels are real (observed) vs generated.
    # NOTE: observed != primary. A watershed_whole cell is observed (real pixels)
    # but is NOT primary, because it came from the unreliable splitting process.
    @property
    def is_observed(self) -> bool:
        """True if every pixel is real (no diffusion-generated content)."""
        return self in (CellSource.SINGLE, CellSource.WATERSHED_WHOLE)

    @property
    def is_reconstructed(self) -> bool:
        """True if the cell contains diffusion-generated pixels."""
        return self is CellSource.INPAINTED


NORMAL = "normal"
ABNORMAL = "abnormal"
_VALID_LABELS = {NORMAL, ABNORMAL}


@dataclass(frozen=True)
class Cell:
    """A single classified cell."""
    source: CellSource
    label: str

    def __post_init__(self):
        if self.label not in _VALID_LABELS:
            raise ValueError(
                f"label must be '{NORMAL}' or '{ABNORMAL}', got {self.label!r}"
            )
        if not isinstance(self.source, CellSource):
            raise TypeError(f"source must be a CellSource, got {type(self.source)}")


@dataclass(frozen=True)
class Biomarker:
    """One biomarker view (A, B, or C)."""
    name: str
    total_cells: int
    abnormal_cells: int

    @property
    def normal_cells(self) -> int:
        return self.total_cells - self.abnormal_cells

    @property
    def abnormal_fraction(self) -> float:
        """Abnormal proportion in [0, 1]; 0.0 when there are no cells."""
        if self.total_cells == 0:
            return 0.0
        return self.abnormal_cells / self.total_cells

    @property
    def per_1000(self) -> float:
        """Abnormal nuclei per 1000 RBCs (the reported biomarker unit)."""
        return self.abnormal_fraction * 1000.0

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "total_cells": self.total_cells,
            "normal_cells": self.normal_cells,
            "abnormal_cells": self.abnormal_cells,
            "abnormal_fraction": round(self.abnormal_fraction, 6),
            "abnormal_per_1000": round(self.per_1000, 2),
        }


@dataclass
class SourceBreakdown:
    """Per-source counts, for the transparency table in the UI/report."""
    source: CellSource
    total: int = 0
    abnormal: int = 0

    @property
    def normal(self) -> int:
        return self.total - self.abnormal

    def as_dict(self) -> dict:
        return {
            "source": self.source.value,
            "total": self.total,
            "normal": self.normal,
            "abnormal": self.abnormal,
        }


@dataclass
class BiomarkerResult:
    """The full three-way result plus the per-source breakdown."""
    real_only: Biomarker          # A (primary)
    combined: Biomarker           # B
    reconstruction_only: Biomarker  # C (exploratory)
    breakdown: dict[str, SourceBreakdown] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "biomarkers": {
                "A_real_only": self.real_only.as_dict(),
                "B_combined": self.combined.as_dict(),
                "C_reconstruction_only": self.reconstruction_only.as_dict(),
            },
            "primary": "A_real_only",
            "exploratory": "C_reconstruction_only",
            "breakdown_by_source": {
                k: v.as_dict() for k, v in self.breakdown.items()
            },
            "notes": (
                "A (real-only) is the primary biomarker: observed cells only. "
                "C (reconstruction-only) is exploratory: it depends on diffusion "
                "inpainting and is reported separately, never as the headline."
            ),
        }


def _count(cells: Iterable[Cell], predicate) -> tuple[int, int]:
    """Return (total, abnormal) over cells matching predicate."""
    total = 0
    abnormal = 0
    for c in cells:
        if predicate(c):
            total += 1
            if c.label == ABNORMAL:
                abnormal += 1
    return total, abnormal


def compute_biomarker(cells: Iterable[Cell]) -> BiomarkerResult:
    """
    Compute the three-way ENA biomarker from an iterable of classified cells.

    A real-only        : source.is_primary        (single cells only) [PRIMARY]
    B combined         : all cells
    C reconstruction   : source.is_reconstruction (watershed_whole + inpainted) [EXPLORATORY]

    Note: watershed_whole cells have real pixels (observed) but are NOT primary,
    because they came from the unreliable multi-cell splitting process. They are
    grouped with inpainted cells in the exploratory reconstruction layer (C).

    Empty input yields zeroed biomarkers (per_1000 = 0.0), not an error.
    """
    cells = list(cells)  # allow multiple passes / reuse

    a_total, a_abn = _count(cells, lambda c: c.source.is_primary)
    b_total, b_abn = _count(cells, lambda c: True)
    c_total, c_abn = _count(cells, lambda c: c.source.is_reconstruction)

    # per-source breakdown for transparency
    breakdown: dict[str, SourceBreakdown] = {
        s.value: SourceBreakdown(s) for s in CellSource
    }
    for c in cells:
        b = breakdown[c.source.value]
        b.total += 1
        if c.label == ABNORMAL:
            b.abnormal += 1

    return BiomarkerResult(
        real_only=Biomarker("A_real_only", a_total, a_abn),
        combined=Biomarker("B_combined", b_total, b_abn),
        reconstruction_only=Biomarker("C_reconstruction_only", c_total, c_abn),
        breakdown=breakdown,
    )


# ------------------------------------------------------------------
# Optional: method-validation helper (AI vs manual counting).
# For comparing the pipeline's count against an expert manual count on the
# SAME material (e.g. against Bandara 2024 manual ENA counts), which is the
# defensible comparison — NOT comparing frequency magnitudes across experiments.
# ------------------------------------------------------------------
@dataclass(frozen=True)
class ValidationComparison:
    manual_abnormal_per_1000: float
    auto_abnormal_per_1000: float

    @property
    def absolute_error(self) -> float:
        return abs(self.auto_abnormal_per_1000 - self.manual_abnormal_per_1000)

    @property
    def relative_error(self) -> float:
        if self.manual_abnormal_per_1000 == 0:
            return 0.0 if self.auto_abnormal_per_1000 == 0 else float("inf")
        return self.absolute_error / self.manual_abnormal_per_1000

    def as_dict(self) -> dict:
        return {
            "manual_abnormal_per_1000": round(self.manual_abnormal_per_1000, 2),
            "auto_abnormal_per_1000": round(self.auto_abnormal_per_1000, 2),
            "absolute_error_per_1000": round(self.absolute_error, 2),
            "relative_error": (
                round(self.relative_error, 4)
                if self.relative_error != float("inf") else None
            ),
        }