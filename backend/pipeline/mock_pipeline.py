"""
Mock pipeline — synthetic cells, no models.

Returns a realistic mix of classified cells so the whole upload -> analyze ->
biomarker flow can be built and tested before real models are wired in.
Proportions loosely mirror the real dataset (mostly normal, ~14% abnormal in
observed cells; inpainted cells skew abnormal, reflecting the measured
reconstruction artifact) so the three-way biomarker looks realistic in the UI.

Deterministic by default (seeded) so tests are stable.
"""

from __future__ import annotations
import random

from core.biomarker import Cell, CellSource, NORMAL, ABNORMAL
from pipeline.base import Pipeline, PipelineResult


class MockPipeline(Pipeline):
    def __init__(self, seed: int = 0):
        self.seed = seed

    def analyze(self, image_bytes: bytes, filename: str = "") -> PipelineResult:
        # seed off the image so the same image gives the same result,
        # but different images vary
        rng = random.Random(self.seed + (len(image_bytes) % 1000))

        cells: list[Cell] = []

        # observed single cells: ~120, ~14% abnormal
        n_single = rng.randint(90, 140)
        for _ in range(n_single):
            label = ABNORMAL if rng.random() < 0.14 else NORMAL
            cells.append(Cell(CellSource.SINGLE, label))

        # watershed whole cells: ~15, ~13% abnormal
        n_whole = rng.randint(8, 20)
        for _ in range(n_whole):
            label = ABNORMAL if rng.random() < 0.13 else NORMAL
            cells.append(Cell(CellSource.WATERSHED_WHOLE, label))

        # inpainted (reconstructed) cells: ~10, skew abnormal (~55%, the measured artifact rate)
        n_inpaint = rng.randint(5, 15)
        for _ in range(n_inpaint):
            label = ABNORMAL if rng.random() < 0.55 else NORMAL
            cells.append(Cell(CellSource.INPAINTED, label))

        meta = {
            "pipeline": self.name,
            "note": "SYNTHETIC cells — no models loaded. For flow testing only.",
            "image_filename": filename,
            "image_bytes": len(image_bytes),
            "stage_counts": {
                "single": n_single,
                "watershed_whole": n_whole,
                "inpainted": n_inpaint,
            },
        }
        return PipelineResult(cells=cells, meta=meta)