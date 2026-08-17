"""
API-level tests for the biomarker endpoint (FastAPI TestClient).

These test the WEB layer: that JSON in -> correct JSON out. The counting
math itself is covered by test_biomarker.py; here we check the endpoint wires
the core up correctly and validates input.
"""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_biomarker_typical():
    payload = {"cells": (
        [{"source": "single", "label": "normal"}] * 100 +
        [{"source": "single", "label": "abnormal"}] * 10 +
        [{"source": "watershed_whole", "label": "normal"}] * 20 +
        [{"source": "watershed_whole", "label": "abnormal"}] * 5 +
        [{"source": "inpainted", "label": "normal"}] * 8 +
        [{"source": "inpainted", "label": "abnormal"}] * 12
    )}
    r = client.post("/biomarker", json=payload)
    assert r.status_code == 200
    d = r.json()
    # A = single + watershed_whole = 135 total, 15 abnormal
    assert d["A_real_only"]["total_cells"] == 135
    assert d["A_real_only"]["abnormal_cells"] == 15
    # B = all = 155 total, 27 abnormal
    assert d["B_combined"]["total_cells"] == 155
    assert d["B_combined"]["abnormal_cells"] == 27
    # C = inpainted = 20 total, 12 abnormal -> 600 per 1000
    assert d["C_reconstruction_only"]["total_cells"] == 20
    assert d["C_reconstruction_only"]["abnormal_per_1000"] == 600.0
    assert d["primary"] == "A_real_only"


def test_biomarker_empty():
    r = client.post("/biomarker", json={"cells": []})
    assert r.status_code == 200
    d = r.json()
    assert d["A_real_only"]["total_cells"] == 0
    assert d["A_real_only"]["abnormal_per_1000"] == 0.0


def test_biomarker_rejects_bad_label():
    r = client.post("/biomarker", json={"cells": [{"source": "single", "label": "weird"}]})
    assert r.status_code == 422   # Pydantic validation error


def test_biomarker_rejects_bad_source():
    r = client.post("/biomarker", json={"cells": [{"source": "magic", "label": "normal"}]})
    assert r.status_code == 422


def test_breakdown_present():
    payload = {"cells": [
        {"source": "single", "label": "abnormal"},
        {"source": "inpainted", "label": "normal"},
    ]}
    d = client.post("/biomarker", json=payload).json()
    sources = {b["source"]: b for b in d["breakdown_by_source"]}
    assert sources["single"]["abnormal"] == 1
    assert sources["inpainted"]["total"] == 1


# ---------- /analyze (mock pipeline, image upload) ----------
def test_analyze_with_image():
    # a tiny fake image payload; content_type marks it as an image
    fake_image = b"\x89PNG\r\n\x1a\n" + b"0" * 200
    r = client.post("/analyze",
                    files={"file": ("smear.png", fake_image, "image/png")})
    assert r.status_code == 200
    d = r.json()
    assert "biomarker" in d and "meta" in d
    # mock flags itself as synthetic
    assert "SYNTHETIC" in d["meta"]["note"]
    # biomarker A is present and sensible
    assert d["biomarker"]["A_real_only"]["total_cells"] > 0
    assert "stage_counts" in d["meta"]


def test_analyze_rejects_non_image():
    r = client.post("/analyze",
                    files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_analyze_rejects_empty():
    r = client.post("/analyze",
                    files={"file": ("empty.png", b"", "image/png")})
    assert r.status_code == 400