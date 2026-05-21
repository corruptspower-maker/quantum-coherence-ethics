"""
QCE Annotated Library -- build_connections.py
Generates connections/connections.pdf from connections/CONNECTIONS.md,
auto-filling cross-references from all annotations/*.yaml files.

Usage:
    py -3 annotations/build_connections.py
"""

import re, yaml
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import textwrap

ROOT        = Path(__file__).parent.parent
ANNOT_DIR   = ROOT / "annotations"
CONN_DIR    = ROOT / "connections"
CONN_DIR.mkdir(exist_ok=True)
OUT_PATH    = CONN_DIR / "connections.pdf"

# Register Caveat
_caveat = str(ANNOT_DIR / "Caveat.ttf")
try:
    pdfmetrics.registerFont(TTFont("Caveat", _caveat))
    HAND_FONT = "Caveat"
except Exception:
    HAND_FONT = "Helvetica-Oblique"

PW, PH     = LETTER
ML, MR     = 1.0*inch, 1.0*inch
MT, MB     = 1.0*inch, 1.0*inch
TW         = PW - ML - MR

INK        = colors.HexColor("#1a1916")
MUTED      = colors.HexColor("#888780")
GOLD       = colors.HexColor("#c09040")
ACCENT     = colors.HexColor("#534AB7")
PAGE_BG    = colors.HexColor("#faf8f2")
RULE       = colors.HexColor("#d3d1c7")


def collect_xrefs():
    """Scan all YAML annotation files, build dict: connections_entry -> [(book_title, section, page_hint)]"""
    xrefs = {}
    for yf in sorted(ANNOT_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8"))
        except Exception:
            continue
        title  = data.get("title", yf.stem)
        author = data.get("author", "")
        for ann in data.get("annotations", []):
            entry = ann.get("connections_entry", "")
            if not entry:
                continue
            if entry not in xrefs:
                xrefs[entry] = []
            xrefs[entry].append({
                "book":    f"{title}",
                "author":  author,
                "section": ann.get("section", ""),
                "label":   ann.get("label", ""),
                "gbo_ref": ann.get("gbo_ref", ""),
            })
    return xrefs


def parse_connections_md(xrefs):
    """Parse CONNECTIONS.md into a list of entry dicts."""
    src = (CONN_DIR / "CONNECTIONS.md").read_text(encoding="utf-8")
    # Split on ## headings
    sections = re.split(r'\n## ', src)
    entries = []
    for sec in sections[1:]:  # skip file header
        lines  = sec.strip().splitlines()
        header = lines[0].strip()   # e.g. "GBO 6.1 -- Preconditions Before a Norm Claim"
        # Find xref anchor in body
        anchor_match = re.search(r'XREF:(\S+)', sec)
        anchor = anchor_match.group(1) if anchor_match else ""
        # Body text = everything between header and the AUTO-GENERATED block
        body = sec
        body = re.sub(r'\*\*Appears in:\*\*.*', '', body, flags=re.DOTALL).strip()
        body = '\n'.join(body.splitlines()[1:]).strip()  # remove header line
        refs = xrefs.get(anchor, [])
        entries.append({
            "header": header,
            "anchor": anchor,
            "body":   body,
            "refs":   refs,
        })
    return entries


def draw_page_bg(c):
    c.setFillColor(PAGE_BG)
    c.rect(0, 0, PW, PH, fill=1, stroke=0)


def draw_header_footer(c, page_num):
    c.setFont("Courier", 8)
    c.setFillColor(MUTED)
    c.drawString(ML, PH - 0.65*inch, "QCE Connections Book")
    c.drawRightString(PW - MR, PH - 0.65*inch, "The Ground Beneath the Ought")
    c.setLineWidth(0.25)
    c.setStrokeColor(RULE)
    c.line(ML, PH - 0.72*inch, PW - MR, PH - 0.72*inch)
    c.drawCentredString(PW/2, 0.45*inch, str(page_num))


def draw_wrapped(c, text, x, y, width, font, size, lead, color=INK, max_y=None):
    """Draw wrapped text, return final y position."""
    if max_y is None:
        max_y = MB
    c.setFont(font, size)
    c.setFillColor(color)
    avg_w  = pdfmetrics.stringWidth("n", font, size)
    chars  = max(10, int(width / avg_w))
    paras  = text.split("\n\n")
    for para in paras:
        para = para.replace("\n", " ").strip()
        if not para:
            y -= lead * 0.5
            continue
        for line in textwrap.wrap(para, chars):
            if y < max_y + lead:
                return y  # caller handles page break
            c.drawString(x, y, line)
            y -= lead
        y -= lead * 0.3
    return y


def build_connections():
    xrefs   = collect_xrefs()
    entries = parse_connections_md(xrefs)

    c        = canvas.Canvas(str(OUT_PATH), pagesize=LETTER)
    c.setTitle("QCE Connections Book")
    c.setAuthor("Power Corrupts & Bereal, Esq.")
    page_num = 1

    draw_page_bg(c)

    # Title page
    y = PH - 2.5*inch
    c.setFont("Times-Bold", 22)
    c.setFillColor(INK)
    c.drawCentredString(PW/2, y, "QCE Connections Book")
    y -= 0.5*inch
    c.setFont("Times-Italic", 13)
    c.setFillColor(MUTED)
    c.drawCentredString(PW/2, y, "The Ground Beneath the Ought -- Cross-Reference Index")
    y -= 0.3*inch
    c.setFont("Courier", 9)
    c.drawCentredString(PW/2, y, "Power Corrupts & Bereal, Esq.  --  2026")
    draw_header_footer(c, page_num)
    c.showPage()
    page_num += 1

    for entry in entries:
        draw_page_bg(c)
        y = PH - MT - 0.3*inch

        # Add named destination for hyperlinking
        if entry["anchor"]:
            c.bookmarkPage(entry["anchor"])

        # Entry header
        c.setFont("Times-Bold", 14)
        c.setFillColor(ACCENT)
        c.drawString(ML, y, entry["header"])
        y -= 0.08*inch
        c.setLineWidth(0.5)
        c.setStrokeColor(GOLD)
        c.line(ML, y, PW - MR, y)
        y -= 0.25*inch

        # Body text
        c.setFont("Times-Roman", 11)
        c.setFillColor(INK)
        for para in entry["body"].split("\n\n"):
            para = para.replace("\n", " ").strip()
            if not para:
                y -= 8
                continue
            avg_w = pdfmetrics.stringWidth("n", "Times-Roman", 11)
            chars = max(10, int(TW / avg_w))
            for line in textwrap.wrap(para, chars):
                if y < MB + 16:
                    draw_header_footer(c, page_num)
                    c.showPage()
                    page_num += 1
                    draw_page_bg(c)
                    y = PH - MT - 0.3*inch
                c.drawString(ML, y, line)
                y -= 16
            y -= 6

        # Cross-references
        if entry["refs"]:
            y -= 0.15*inch
            c.setFont("Courier", 8)
            c.setFillColor(MUTED)
            c.drawString(ML, y, "Appears in:")
            y -= 14
            c.setLineWidth(0.25)
            c.setStrokeColor(RULE)
            c.line(ML, y + 10, PW - MR, y + 10)
            for ref in entry["refs"]:
                if y < MB + 16:
                    draw_header_footer(c, page_num)
                    c.showPage()
                    page_num += 1
                    draw_page_bg(c)
                    y = PH - MT - 0.3*inch
                line = f"  {ref['book']} -- {ref['section']}"
                c.setFont("Courier", 8)
                c.setFillColor(INK)
                c.drawString(ML, y, line)
                y -= 12

        draw_header_footer(c, page_num)
        c.showPage()
        page_num += 1

    c.save()
    print(f"Connections Book saved ({page_num-1} pages)")


if __name__ == "__main__":
    build_connections()
