from __future__ import annotations
import os
import glob
import json
import logging
from textwrap import wrap
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm


logger = logging.getLogger("finbot.report")


def _add_heading(c: canvas.Canvas, text: str, y: float) -> float:
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, text)
    return y - 0.6 * cm


def _add_paragraph(c: canvas.Canvas, text: str | None, y: float, width: float, height: float, font_size: int = 10) -> float:
    c.setFont("Helvetica", font_size)
    safe_text = text or ""
    max_width = int((width - 4 * cm) / (font_size * 0.5))
    for line in wrap(safe_text, max_width):
        c.drawString(2 * cm, y, line)
        y -= 0.5 * cm
        if y < 2 * cm:
            c.showPage()
            y = height - 2 * cm
            c.setFont("Helvetica", font_size)
    return y - 0.3 * cm


def generate_pdf_report(run_dir: str) -> str:
    """Generate a comprehensive PDF report under the given run_dir.

    The function expects a `bundle.json` in run_dir and optional critique files
    named `critique_round*.json`. Returns the path to the written PDF.
    """
    bundle_path = os.path.join(run_dir, "bundle.json")
    assert os.path.exists(bundle_path), f"bundle.json not found in {run_dir}"

    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    pdf_path = os.path.join(run_dir, "report.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    y = height - 2 * cm
    title = f"FinBot Report: {bundle['input']['name']} ({bundle['input']['yf_symbol']})"
    y = _add_heading(c, title, y)

    # 1) Input & Profile
    y = _add_heading(c, "1) Input & Profile", y)
    y = _add_paragraph(c, f"Risk: {bundle['profile'].get('risk_level')} | Horizon: {bundle['profile'].get('horizon_years')} years", y, width, height)

    # 2) Ticker
    y = _add_heading(c, "2) Ticker", y)
    y = _add_paragraph(c, f"Symbol: {bundle['input'].get('symbol')} | Yahoo: {bundle['input'].get('yf_symbol')}", y, width, height)

    # 3) Fundamentals
    y = _add_heading(c, "3) Fundamentals", y)
    y = _add_paragraph(c, f"Score: {bundle['fundamentals'].get('score')}", y, width, height)
    y = _add_paragraph(c, f"Pros: {', '.join(bundle['fundamentals'].get('pros', []) or [])}", y, width, height)
    y = _add_paragraph(c, f"Cons: {', '.join(bundle['fundamentals'].get('cons', []) or [])}", y, width, height)

    # 4) Technical
    y = _add_heading(c, "4) Technical", y)
    y = _add_paragraph(c, f"Trend: {bundle['technical'].get('trend')}", y, width, height)
    y = _add_paragraph(c, f"Metrics: {bundle['technical'].get('metrics')}", y, width, height)

    # 5) News
    y = _add_heading(c, "5) News Summary", y)
    y = _add_paragraph(c, bundle['news'].get('summary'), y, width, height)

    # 6) Sector/Macro
    y = _add_heading(c, "6) Sector/Macro", y)
    y = _add_paragraph(c, bundle['sector_macro'].get('summary'), y, width, height)

    # 7) Alternatives
    y = _add_heading(c, "7) Alternatives", y)
    alts = bundle['alternatives'].get('candidates', []) or []
    alt_text = "; ".join([f"{cnd.get('name')}: {cnd.get('reason')}" for cnd in alts])
    y = _add_paragraph(c, alt_text, y, width, height)

    # 8) Committee Discussion
    y = _add_heading(c, "8) Committee Discussion", y)
    try:
        crits = sorted(glob.glob(os.path.join(run_dir, "critique_round*.json")))
        if not crits:
            y = _add_paragraph(c, "No committee rounds recorded.", y, width, height)
        else:
            for cp in crits:
                with open(cp, "r", encoding="utf-8") as f:
                    dat = json.load(f)
                    y = _add_paragraph(c, f"Round {dat.get('round')}: {dat.get('text','')}", y, width, height)
    except Exception as e:
        logger.debug("Failed to include committee critiques: %s", e)
        y = _add_paragraph(c, "Committee discussion could not be loaded.", y, width, height)

    # 9) Final decision
    y = _add_heading(c, "9) Final Decision", y)
    dec = bundle.get('decision', {})
    y = _add_paragraph(c, f"Decision: {dec.get('decision')}", y, width, height)
    y = _add_paragraph(c, f"Confidence: {dec.get('confidence')}", y, width, height)
    y = _add_paragraph(c, f"Entry Timing: {dec.get('entry_timing')}", y, width, height)
    y = _add_paragraph(c, f"Position Size: {dec.get('position_size')}", y, width, height)
    y = _add_paragraph(c, f"DCA Plan: {dec.get('dca_plan')}", y, width, height)
    y = _add_paragraph(c, f"Risk Controls: {dec.get('risk_controls')}", y, width, height)
    y = _add_paragraph(c, f"Rationale: {dec.get('rationale')}", y, width, height)

    c.showPage()
    c.save()
    logger.info("Saved PDF report: %s", pdf_path)
    return pdf_path


