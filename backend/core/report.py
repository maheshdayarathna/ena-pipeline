"""
PDF result-sheet generator.

Builds a professional one-page ENA biomarker report from a stored analysis
record (numbers only — images are not stored). Used by GET /report/{id}.
"""

from __future__ import annotations
import io
from datetime import datetime
from typing import Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)

NAVY = colors.HexColor("#1F3864")
BLUE = colors.HexColor("#2E5496")
LIGHT = colors.HexColor("#D9E2F3")
GREY = colors.HexColor("#666666")


def _fmt_dt(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return iso or "-"


def build_report_pdf(a: Dict[str, Any]) -> bytes:
    """Return PDF bytes for one analysis record `a` (from storage)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=20 * mm, bottomMargin=18 * mm,
        leftMargin=20 * mm, rightMargin=20 * mm,
        title=f"ENA Biomarker Report #{a.get('id','')}",
    )
    styles = getSampleStyleSheet()
    h_title = ParagraphStyle("t", parent=styles["Title"], textColor=NAVY, fontSize=20, spaceAfter=2)
    h_sub = ParagraphStyle("s", parent=styles["Normal"], textColor=GREY, fontSize=10, spaceAfter=14)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=BLUE, fontSize=13, spaceBefore=10, spaceAfter=6)
    body = ParagraphStyle("b", parent=styles["Normal"], fontSize=10, leading=15)
    small = ParagraphStyle("sm", parent=styles["Normal"], fontSize=8.5, textColor=GREY, leading=12)

    story = []

    # header
    story.append(Paragraph("ENA Biomarker Report", h_title))
    story.append(Paragraph(
        "Automated erythrocyte nuclear abnormality analysis &mdash; Nile tilapia blood smear",
        h_sub))

    # metadata table
    meta_rows = [
        ["Report ID", str(a.get("id", "-"))],
        ["Date analysed", _fmt_dt(a.get("created_at", ""))],
        ["Image file", a.get("filename") or "-"],
        ["Diffusion reconstruction", "Enabled" if a.get("use_diffusion") else "Disabled"],
    ]
    mt = Table(meta_rows, colWidths=[55 * mm, 105 * mm])
    mt.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), GREY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#DDDDDD")),
    ]))
    story.append(mt)

    # primary result — big
    story.append(Paragraph("Primary biomarker (A &mdash; observed single cells)", h2))
    a_per = a.get("a_per_1000", 0)
    a_tot = a.get("a_total", 0)
    a_abn = a.get("a_abnormal", 0)
    prim = Table(
        [[Paragraph(f"<b>{a_per:.1f}</b>", ParagraphStyle('big', parent=body, fontSize=30, textColor=NAVY)),
          Paragraph("abnormal nuclei<br/>per 1,000 RBCs", body)],
         [Paragraph(f"{a_tot} cells &nbsp;&bull;&nbsp; {a_tot - a_abn} normal &nbsp;&bull;&nbsp; {a_abn} abnormal", body), ""]],
        colWidths=[70 * mm, 90 * mm])
    prim.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF3FB")),
        ("BOX", (0, 0), (-1, -1), 1, BLUE),
        ("SPAN", (0, 1), (1, 1)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(prim)
    story.append(Paragraph(
        "Biomarker A is the primary, validated measurement, computed from cells "
        "detected directly as single cells. It is the authoritative result.", small))

    # three-way table
    story.append(Paragraph("Three-way biomarker comparison", h2))
    hdr = ["Biomarker", "Total cells", "Normal", "Abnormal", "Per 1,000 RBCs"]
    rows = [hdr,
            ["A &mdash; Real-only (primary)", a.get("a_total"), a.get("a_total", 0) - a.get("a_abnormal", 0),
             a.get("a_abnormal"), f"{a.get('a_per_1000', 0):.1f}"],
            ["B &mdash; Combined", a.get("b_total"), a.get("b_total", 0) - a.get("b_abnormal", 0),
             a.get("b_abnormal"), f"{a.get('b_per_1000', 0):.1f}"],
            ["C &mdash; Reconstruction (exploratory)", a.get("c_total"), a.get("c_total", 0) - a.get("c_abnormal", 0),
             a.get("c_abnormal"), f"{a.get('c_per_1000', 0):.1f}"]]
    rows = [[Paragraph(str(c), body) if isinstance(c, str) else str(c) for c in r] for r in rows]
    tw = Table(rows, colWidths=[62 * mm, 24 * mm, 22 * mm, 24 * mm, 28 * mm])
    tw.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#EEF3FB")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(tw)

    # stage counts
    sc = a.get("stage_counts") or {}
    if sc:
        story.append(Paragraph("Pipeline stage breakdown", h2))
        sc_rows = [[k.replace("_", " ").title(), str(v)] for k, v in sc.items()]
        st = Table(sc_rows, colWidths=[80 * mm, 30 * mm])
        st.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), GREY),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#EEEEEE")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(st)

    # footer / notes
    story.append(Spacer(1, 14))
    story.append(Paragraph(
        "<b>Notes.</b> Biomarker A (single observed cells) is the validated primary measure. "
        "Biomarker C (reconstruction) combines watershed-split and diffusion-inpainted cells and is "
        "exploratory only; it typically reads higher due to reconstruction artefacts and should not be "
        "used as the headline figure. Detection and classification carry the model's characterised error "
        "(detection mAP@50 &asymp; 0.76; classification ROC-AUC 0.913, abnormal recall 0.72).", small))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Generated by the ENA Biomarker application. This is an automated research tool; "
        "results are a proof-of-concept measurement, not a clinical diagnosis.", small))

    doc.build(story)
    buf.seek(0)
    return buf.read()