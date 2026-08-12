"""
ENA biomarker API (FastAPI).

Wraps the tested counting core (core/biomarker.py) in a web service.
For now it computes the three-way biomarker from a list of already-classified
cells. Model inference (detection -> watershed -> classification -> inpainting)
will be added as a later endpoint that produces those cells from an image.

Run:  uvicorn main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.biomarker import Cell, CellSource, compute_biomarker
from core.schemas import BiomarkerRequest, BiomarkerResponse

app = FastAPI(
    title="ENA Biomarker API",
    description=(
        "Automated erythrocyte nuclear abnormality (ENA) biomarker for tilapia "
        "blood smears. Computes the three-way biomarker: A real-only (primary), "
        "B combined, C reconstruction-only (exploratory)."
    ),
    version="0.1.0",
)

# Allow the React dev server (localhost:5173 / 3000) to call this API in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok", "service": "ena-biomarker", "version": app.version}


@app.post("/biomarker", response_model=BiomarkerResponse, tags=["biomarker"])
def biomarker(req: BiomarkerRequest) -> BiomarkerResponse:
    """
    Compute the three-way ENA biomarker from a batch of classified cells.

    Each cell has a `source` (single / watershed_whole / inpainted) and a
    `label` (normal / abnormal). Returns biomarkers A, B, C plus a per-source
    breakdown. Empty input returns zeroed biomarkers, not an error.
    """
    cells = [Cell(CellSource(c.source), c.label) for c in req.cells]
    result = compute_biomarker(cells)
    d = result.as_dict()
    bm = d["biomarkers"]
    return BiomarkerResponse(
        A_real_only=bm["A_real_only"],
        B_combined=bm["B_combined"],
        C_reconstruction_only=bm["C_reconstruction_only"],
        breakdown_by_source=list(d["breakdown_by_source"].values()),
        notes=d["notes"],
    )