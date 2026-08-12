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