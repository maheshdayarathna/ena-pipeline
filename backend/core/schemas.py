"""
API schemas (request/response models) for the ENA biomarker service.

These Pydantic models define and validate the JSON shape at the web boundary.
They are separate from core/biomarker.py (pure domain logic) so the web layer
can change without touching the tested counting core.
"""

from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, Field

from core.biomarker import CellSource, NORMAL, ABNORMAL


class CellIn(BaseModel):
    """One classified cell as received over the API."""
    source: Literal["single", "watershed_whole", "inpainted"] = Field(
        ..., description="How the cell was obtained."
    )
    label: Literal["normal", "abnormal"] = Field(
        ..., description="Classifier call for the cell."
    )

    model_config = {
        "json_schema_extra": {
            "example": {"source": "single", "label": "abnormal"}
        }
    }


class BiomarkerRequest(BaseModel):
    """A batch of classified cells to compute the three-way biomarker from."""
    cells: List[CellIn] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "example": {
                "cells": [
                    {"source": "single", "label": "normal"},
                    {"source": "single", "label": "abnormal"},
                    {"source": "watershed_whole", "label": "normal"},
                    {"source": "inpainted", "label": "abnormal"},
                ]
            }
        }
    }


class BiomarkerView(BaseModel):
    name: str
    total_cells: int
    normal_cells: int
    abnormal_cells: int
    abnormal_fraction: float
    abnormal_per_1000: float


class SourceBreakdownOut(BaseModel):
    source: str
    total: int
    normal: int
    abnormal: int


class BiomarkerResponse(BaseModel):
    A_real_only: BiomarkerView
    B_combined: BiomarkerView
    C_reconstruction_only: BiomarkerView
    breakdown_by_source: List[SourceBreakdownOut]
    primary: str = "A_real_only"
    exploratory: str = "C_reconstruction_only"
    notes: str