"""
ENA biomarker API (FastAPI).

Endpoints:
  GET  /health     - liveness check
  POST /biomarker  - compute biomarker from a list of already-classified cells
  POST /analyze    - upload a smear image -> run pipeline -> biomarker

The pipeline is currently the MOCK (synthetic cells, no models) so the full
upload->count flow can be tested. Swapping in the real model-backed pipeline
is a one-line change (see get_pipeline()).

Run:  uvicorn main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.biomarker import Cell, CellSource, compute_biomarker
from core.schemas import BiomarkerRequest, BiomarkerResponse
from pipeline.base import Pipeline
from pipeline.mock_pipeline import MockPipeline

app = FastAPI(
    title="ENA Biomarker API",
    description=(
        "Automated erythrocyte nuclear abnormality (ENA) biomarker for tilapia "
        "blood smears. Three-way biomarker: A real-only (primary), B combined, "
        "C reconstruction-only (exploratory)."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- pipeline selection (swap mock -> real here later) ----
def get_pipeline() -> Pipeline:
    return MockPipeline()


def _biomarker_payload(result) -> BiomarkerResponse:
    d = result.as_dict()
    bm = d["biomarkers"]
    return BiomarkerResponse(
        A_real_only=bm["A_real_only"],
        B_combined=bm["B_combined"],
        C_reconstruction_only=bm["C_reconstruction_only"],
        breakdown_by_source=list(d["breakdown_by_source"].values()),
        notes=d["notes"],
    )


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "ena-biomarker", "version": app.version}


@app.post("/biomarker", response_model=BiomarkerResponse, tags=["biomarker"])
def biomarker(req: BiomarkerRequest) -> BiomarkerResponse:
    """Compute the three-way biomarker from a batch of classified cells."""
    cells = [Cell(CellSource(c.source), c.label) for c in req.cells]
    return _biomarker_payload(compute_biomarker(cells))


@app.post("/analyze", tags=["biomarker"])
async def analyze(file: UploadFile = File(...)) -> dict:
    """
    Upload a smear image -> run the pipeline -> three-way biomarker.

    Currently uses the MOCK pipeline (synthetic cells). The response includes
    a 'meta' block flagging that the cells are synthetic and giving per-stage
    counts, so it is obvious in the UI that no real models are loaded yet.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload an image file.")
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    pipe = get_pipeline()
    result = pipe.analyze(image_bytes, filename=file.filename or "")
    biomarker_resp = _biomarker_payload(compute_biomarker(result.cells))

    return {
        "biomarker": biomarker_resp.model_dump(),
        "meta": result.meta,
    }