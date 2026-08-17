"""
Pipeline interface.

Defines the contract every pipeline must satisfy: given an image, return a
list of classified Cell objects (tagged by source + label) ready for the
counting core. The mock pipeline and the real (model-backed) pipeline both
implement this, so they are interchangeable — main.py depends on the
interface, not on a concrete implementation.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from core.biomarker import Cell


@dataclass
class PipelineResult:
    """What a pipeline returns for one image."""
    cells: List[Cell]
    # optional diagnostics for the UI / debugging (counts by stage, etc.)
    meta: dict = field(default_factory=dict)


class Pipeline(ABC):
    """Abstract pipeline: image bytes -> classified cells."""

    @abstractmethod
    def analyze(self, image_bytes: bytes, filename: str = "", use_diffusion: bool = False) -> PipelineResult:
        """
        Run the full pipeline on one image and return classified cells.

        Implementations do: detect -> (single | multi-cell) ->
        watershed for multi-cell -> classify whole cells ->
        inpaint clipped cells -> classify. The mock skips all that and
        returns synthetic cells.
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__