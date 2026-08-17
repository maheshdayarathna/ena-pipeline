"""
ENA biomarker API (FastAPI).

Endpoints:
  GET  /health     - liveness check
  POST /biomarker  - compute biomarker from a list of already-classified cells
  POST /analyze    - upload a smear image -> run pipeline -> biomarker

The pipeline (RealPipeline: YOLO detection + DenseNet classification) is loaded
ONCE at server startup and reused for every request, so models are not reloaded
per upload. To swap pipelines, change build_pipeline().

Run:  uvicorn main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from core.biomarker import Cell, CellSource, compute_biomarker
from core.schemas import BiomarkerRequest, BiomarkerResponse
from pipeline.base import Pipeline
from pipeline.mock_pipeline import MockPipeline
from pipeline.real_pipeline import RealPipeline


# ---- choose which pipeline the app uses ----
def build_pipeline() -> Pipeline:
    # swap to MockPipeline() if you want to run without models
    return RealPipeline()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # runs ONCE at startup: build the pipeline (models load here, not per request)
    print("Loading pipeline (this loads the models once)...")
    app.state.pipeline = build_pipeline()
    print("Pipeline ready.")
    yield
    # (nothing to clean up on shutdown)


app = FastAPI(
    title="ENA Biomarker API",
    description=(
        "Automated erythrocyte nuclear abnormality (ENA) biomarker for tilapia "
        "blood smears. Three-way biomarker: A real-only (primary), B combined, "
        "C reconstruction-only (exploratory)."
    ),
    version="0.3.0",
    lifespan=lifespan,
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
async def analyze(request: Request, file: UploadFile = File(...)) -> dict:
    """
    Upload a smear image -> run the (pre-loaded) pipeline -> three-way biomarker.
    The pipeline is reused from app.state, so models are not reloaded per request.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload an image file.")
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    pipe: Pipeline = request.app.state.pipeline
    result = pipe.analyze(image_bytes, filename=file.filename or "")
    biomarker_resp = _biomarker_payload(compute_biomarker(result.cells))

    return {
        "biomarker": biomarker_resp.model_dump(),
        "meta": result.meta,
    }