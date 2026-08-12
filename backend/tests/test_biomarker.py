"""
Unit tests for the ENA biomarker counting core.

Each test states the hand-calculated expected value in a comment, so the
logic is verified against numbers a human worked out, not against itself.
Run:  pytest -v   (from backend/)  or  python -m pytest
"""

import math
import pytest

from core.biomarker import (
    Cell, CellSource, compute_biomarker, ValidationComparison,
    NORMAL, ABNORMAL,
)


# ---------- helpers ----------
def make(source, n_normal, n_abnormal):
    return ([Cell(source, NORMAL) for _ in range(n_normal)] +
            [Cell(source, ABNORMAL) for _ in range(n_abnormal)])


# ---------- core three-way computation ----------
def test_typical_mixed_case():
    # Hand-worked scenario:
    #   single         : 100 normal,  10 abnormal
    #   watershed_whole:  20 normal,   5 abnormal
    #   inpainted      :   8 normal,  12 abnormal
    cells = (make(CellSource.SINGLE, 100, 10) +
             make(CellSource.WATERSHED_WHOLE, 20, 5) +
             make(CellSource.INPAINTED, 8, 12))
    r = compute_biomarker(cells)

    # A real-only = single + watershed_whole = 135 total, 15 abnormal
    assert r.real_only.total_cells == 135
    assert r.real_only.abnormal_cells == 15
    # 15/135 * 1000 = 111.11...
    assert math.isclose(r.real_only.per_1000, 15/135*1000, rel_tol=1e-9)

    # B combined = all = 155 total, 27 abnormal
    assert r.combined.total_cells == 155
    assert r.combined.abnormal_cells == 27
    assert math.isclose(r.combined.per_1000, 27/155*1000, rel_tol=1e-9)

    # C reconstruction-only = inpainted = 20 total, 12 abnormal
    assert r.reconstruction_only.total_cells == 20
    assert r.reconstruction_only.abnormal_cells == 12
    assert math.isclose(r.reconstruction_only.per_1000, 12/20*1000, rel_tol=1e-9)  # 600.0


def test_A_excludes_inpainted():
    # Only inpainted cells are abnormal; A must NOT see them.
    cells = make(CellSource.SINGLE, 50, 0) + make(CellSource.INPAINTED, 0, 10)
    r = compute_biomarker(cells)
    assert r.real_only.abnormal_cells == 0          # A sees no abnormal
    assert r.real_only.per_1000 == 0.0
    assert r.combined.abnormal_cells == 10          # B sees them
    assert r.reconstruction_only.abnormal_cells == 10  # C is all of them


def test_watershed_whole_counts_as_observed():
    # watershed_whole is OBSERVED (real pixels) -> belongs in A.
    cells = make(CellSource.WATERSHED_WHOLE, 0, 4)
    r = compute_biomarker(cells)
    assert r.real_only.total_cells == 4
    assert r.real_only.abnormal_cells == 4
    assert r.reconstruction_only.total_cells == 0   # not reconstructed


def test_combined_equals_A_plus_C_totals():
    # Invariant: B.total == A.total + C.total  (partition property)
    cells = (make(CellSource.SINGLE, 30, 3) +
             make(CellSource.WATERSHED_WHOLE, 10, 1) +
             make(CellSource.INPAINTED, 5, 5))
    r = compute_biomarker(cells)
    assert r.combined.total_cells == r.real_only.total_cells + r.reconstruction_only.total_cells
    assert r.combined.abnormal_cells == r.real_only.abnormal_cells + r.reconstruction_only.abnormal_cells


# ---------- edge cases ----------
def test_empty_input():
    r = compute_biomarker([])
    for bm in (r.real_only, r.combined, r.reconstruction_only):
        assert bm.total_cells == 0
        assert bm.abnormal_cells == 0
        assert bm.per_1000 == 0.0          # no divide-by-zero


def test_all_normal():
    cells = make(CellSource.SINGLE, 200, 0)
    r = compute_biomarker(cells)
    assert r.real_only.per_1000 == 0.0
    assert r.real_only.normal_cells == 200


def test_no_reconstruction_case():
    # A pipeline run with no clipped cells -> C is empty, A == B.
    cells = make(CellSource.SINGLE, 90, 10) + make(CellSource.WATERSHED_WHOLE, 10, 0)
    r = compute_biomarker(cells)
    assert r.reconstruction_only.total_cells == 0
    assert r.real_only.total_cells == r.combined.total_cells
    assert r.real_only.abnormal_cells == r.combined.abnormal_cells


def test_breakdown_by_source():
    cells = (make(CellSource.SINGLE, 5, 2) +
             make(CellSource.WATERSHED_WHOLE, 3, 1) +
             make(CellSource.INPAINTED, 1, 4))
    r = compute_biomarker(cells)
    b = r.breakdown
    assert b["single"].total == 7 and b["single"].abnormal == 2
    assert b["watershed_whole"].total == 4 and b["watershed_whole"].abnormal == 1
    assert b["inpainted"].total == 5 and b["inpainted"].abnormal == 4


def test_invalid_label_rejected():
    with pytest.raises(ValueError):
        Cell(CellSource.SINGLE, "weird")


def test_as_dict_shape():
    r = compute_biomarker(make(CellSource.SINGLE, 10, 2))
    d = r.as_dict()
    assert d["primary"] == "A_real_only"
    assert d["biomarkers"]["A_real_only"]["abnormal_per_1000"] == round(2/12*1000, 2)
    assert "breakdown_by_source" in d


# ---------- validation comparison (AI vs manual) ----------
def test_validation_comparison():
    # Manual (expert) = 10.47 per 1000; auto (pipeline) = 9.80 per 1000.
    v = ValidationComparison(manual_abnormal_per_1000=10.47, auto_abnormal_per_1000=9.80)
    assert math.isclose(v.absolute_error, 0.67, abs_tol=1e-9)
    assert math.isclose(v.relative_error, 0.67/10.47, rel_tol=1e-9)


def test_validation_zero_manual():
    v = ValidationComparison(0.0, 0.0)
    assert v.relative_error == 0.0
    v2 = ValidationComparison(0.0, 5.0)
    assert v2.relative_error == float("inf")
    assert v2.as_dict()["relative_error"] is None