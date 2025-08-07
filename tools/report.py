from __future__ import annotations
import os
import glob
import json
import logging
from textwrap import wrap
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# Optional dependencies for MD/HTML conversion
try:
    import markdown as _md
except Exception:
    _md = None

try:
    from weasyprint import HTML, CSS  # type: ignore
except Exception:
    HTML = None
    CSS = None


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


def generate_markdown_report(run_dir: str) -> tuple[str, str]:
    """Generate a markdown report and HTML in run_dir from bundle and critiques.

    Returns (md_path, html_path).
    """
    bundle_path = os.path.join(run_dir, "bundle.json")
    assert os.path.exists(bundle_path), f"bundle.json not found in {run_dir}"

    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    lines: list[str] = []
    lines.append(f"# FinBot Report: {bundle['input']['name']} ({bundle['input']['yf_symbol']})")
    lines.append("")
    lines.append("## 1) Input & Profile")
    lines.append(f"- Risk: {bundle['profile'].get('risk_level')}")
    lines.append(f"- Horizon (years): {bundle['profile'].get('horizon_years')}")
    lines.append("")
    lines.append("## 2) Ticker")
    lines.append(f"- Symbol: {bundle['input'].get('symbol')}")
    lines.append(f"- Yahoo: {bundle['input'].get('yf_symbol')}")
    lines.append("")
    lines.append("## 3) Fundamentals")
    lines.append(f"- Score: {bundle['fundamentals'].get('score')}")
    pros = bundle['fundamentals'].get('pros', []) or []
    cons = bundle['fundamentals'].get('cons', []) or []
    if pros:
        lines.append("- Pros:")
        for p in pros:
            lines.append(f"  - {p}")
    if cons:
        lines.append("- Cons:")
        for c_ in cons:
            lines.append(f"  - {c_}")
    lines.append("")
    lines.append("## 4) Technical")
    lines.append(f"- Trend: {bundle['technical'].get('trend')}")
    lines.append(f"- Metrics: `{bundle['technical'].get('metrics')}`")
    lines.append("")
    lines.append("## 5) News Summary")
    lines.append(bundle['news'].get('summary') or "")
    lines.append("")
    lines.append("## 6) Sector/Macro")
    lines.append(bundle['sector_macro'].get('summary') or "")
    lines.append("")
    lines.append("## 7) Alternatives")
    alts = bundle['alternatives'].get('candidates', []) or []
    if alts:
        for cnd in alts:
            lines.append(f"- {cnd.get('name')}: {cnd.get('reason')}")
    else:
        lines.append("- None")
    lines.append("")
    lines.append("## 8) Committee Discussion")
    try:
        crits = sorted(glob.glob(os.path.join(run_dir, "critique_round*.json")))
        if not crits:
            lines.append("- No committee rounds recorded.")
        else:
            for cp in crits:
                with open(cp, "r", encoding="utf-8") as f:
                    dat = json.load(f)
                    lines.append(f"### Round {dat.get('round')}")
                    lines.append("")
                    lines.append(dat.get('text', '') or '')
                    lines.append("")
    except Exception as e:
        logger.debug("Failed to include committee critiques: %s", e)
        lines.append("- Committee discussion could not be loaded.")
    lines.append("")
    lines.append("## 9) Final Decision")
    dec = bundle.get('decision', {})
    lines.append(f"- Decision: {dec.get('decision')}")
    lines.append(f"- Confidence: {dec.get('confidence')}")
    lines.append(f"- Entry Timing: {dec.get('entry_timing')}")
    lines.append(f"- Position Size: {dec.get('position_size')}")
    lines.append(f"- DCA Plan: {dec.get('dca_plan')}")
    lines.append(f"- Risk Controls: `{dec.get('risk_controls')}`")
    lines.append(f"- Rationale: {dec.get('rationale')}")

    md_text = "\n".join(lines)
    md_path = os.path.join(run_dir, "report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    # Build HTML (if markdown lib available)
    if _md is not None:
        html_body = _md.markdown(md_text, extensions=["fenced_code", "tables", "toc"])  # type: ignore
    else:
        html_body = "<pre>" + md_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") + "</pre>"

    css = """
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, 'Apple Color Emoji',
           'Segoe UI Emoji', 'Segoe UI Symbol'; line-height: 1.5; padding: 24px; }
    h1 { font-size: 24px; margin-top: 0; }
    h2 { font-size: 18px; margin-top: 20px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
    h3 { font-size: 16px; margin-top: 16px; }
    code, pre { background: #f6f8fa; padding: 2px 4px; border-radius: 4px; }
    ul { margin-left: 20px; }
    table { border-collapse: collapse; }
    th, td { border: 1px solid #ccc; padding: 4px 8px; }
    """
    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>{css}</style>
  <title>FinBot Report</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light dark" />
</head>
<body>
{html_body}
</body>
</html>
"""
    html_path = os.path.join(run_dir, "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info("Saved Markdown and HTML report: %s, %s", md_path, html_path)
    return md_path, html_path


def convert_markdown_to_pdf(md_path: str) -> str:
    """Convert the given MD (or its sibling HTML) to PDF using WeasyPrint if available.

    Falls back to the legacy reportlab PDF if conversion is not possible.
    """
    run_dir = os.path.dirname(md_path)
    html_path = os.path.join(run_dir, "report.html")
    pdf_path = os.path.join(run_dir, "report.pdf")
    if HTML is None or CSS is None or not os.path.exists(html_path):
        logger.info("WeasyPrint not available or HTML missing; falling back to basic PDF generator")
        return generate_pdf_report(run_dir)
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    HTML(string=html, base_url=run_dir).write_pdf(pdf_path)
    logger.info("Saved PDF report (from Markdown): %s", pdf_path)
    return pdf_path

