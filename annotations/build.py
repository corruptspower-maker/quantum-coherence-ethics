"""
QCE Annotated Library — build.py
Typesets a Gutenberg plain-text book into a PDF with wide right margin,
then overlays annotations from the book's YAML file.

Usage:
    py -3 annotations/build.py hume-treatise
    py -3 annotations/build.py --all
"""

import sys, re, yaml, textwrap
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
ANNOT_DIR  = ROOT / "annotations"
OUTPUT_DIR = ROOT / "assets" / "books"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Page geometry (from BIBLE.md) ─────────────────────────────────────────
PW, PH      = LETTER                  # 612 × 792 pt
MARGIN_L    = 1.0 * inch
MARGIN_T    = 1.0 * inch
MARGIN_B    = 1.0 * inch
MARGIN_R    = 3.0 * inch              # annotation zone
TEXT_W      = PW - MARGIN_L - MARGIN_R
ANNOT_X     = PW - MARGIN_R + 0.25 * inch
ANNOT_W     = MARGIN_R - 0.35 * inch

# ── Typography ────────────────────────────────────────────────────────────
BODY_FONT   = "Times-Roman"           # built-in serif (EB Garamond needs TTF)
BODY_BOLD   = "Times-Bold"
BODY_SIZE   = 11
BODY_LEAD   = 16
MONO_FONT   = "Courier"
MONO_SIZE   = 8
_caveat_path = str(ANNOT_DIR / "Caveat.ttf")
try:
    pdfmetrics.registerFont(TTFont("Caveat", _caveat_path))
    ANNOT_FONT = "Caveat"
except Exception:
    ANNOT_FONT = "Helvetica-Oblique"   # fallback
ANNOT_SIZE  = 8.5
ANNOT_LEAD  = 12

INK         = colors.HexColor("#1a1916")
MUTED       = colors.HexColor("#888780")
ANNOT_INK   = colors.HexColor("#5c3a1e")
GOLD        = colors.HexColor("#c09040")
PAGE_BG     = colors.HexColor("#faf8f2")


def clean_gutenberg(text):
    """Strip Gutenberg header/footer boilerplate and normalise whitespace."""
    # Remove everything before the actual text starts
    start = re.search(r'\*\*\* START OF THE PROJECT GUTENBERG', text)
    end   = re.search(r'\*\*\* END OF THE PROJECT GUTENBERG',   text)
    if start:
        text = text[start.end():]
    if end:
        text = text[:end.start()]
    # Collapse excessive blank lines to max 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def wrap_text(text, font, size, width, c_obj):
    """Wrap text to fit in width, return list of lines."""
    # Approximate character width
    avg_char_w = pdfmetrics.stringWidth("n", font, size)
    chars_per_line = max(10, int(width / avg_char_w))
    lines = []
    for para in text.split('\n\n'):
        para = para.replace('\n', ' ').strip()
        if not para:
            lines.append(('', False))
            continue
        wrapped = textwrap.wrap(para, chars_per_line)
        for i, line in enumerate(wrapped):
            lines.append((line, i == 0))  # (text, is_first_line_of_para)
        lines.append(('', False))
    return lines


def build_book(slug):
    yaml_path = ANNOT_DIR / f"{slug}.yaml"
    txt_path  = ANNOT_DIR / f"{slug}.txt"
    out_path  = OUTPUT_DIR / f"{slug}.pdf"

    # Load annotation data if exists
    annotations = []
    meta = {"title": slug, "author": ""}
    if yaml_path.exists():
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        meta = data
        annotations = data.get("annotations", [])

    # Load and clean text
    if not txt_path.exists():
        print(f"ERROR: {txt_path} not found. Download it first.")
        sys.exit(1)
    raw = txt_path.read_text(encoding="utf-8", errors="replace")
    text = clean_gutenberg(raw)

    print(f"Typesetting {meta['title']} ({len(text):,} chars) ...")

    c = canvas.Canvas(str(out_path), pagesize=LETTER)
    c.setTitle(meta["title"])
    c.setAuthor(meta.get("author", ""))

    lines = wrap_text(text, BODY_FONT, BODY_SIZE, TEXT_W, c)

    # Build an index: passage text → annotation
    annot_index = {}
    for a in annotations:
        key = a.get("passage", "")[:60].strip()
        annot_index[key] = a

    page_num    = 1
    y           = PH - MARGIN_T
    line_count  = 0
    pending_annots = []   # annotations to draw on current page

    def new_page():
        nonlocal y, page_num
        # Draw header
        c.setFont(MONO_FONT, MONO_SIZE)
        c.setFillColor(MUTED)
        c.drawString(MARGIN_L, PH - 0.65 * inch, meta["title"])
        c.drawRightString(PW - MARGIN_R * 0.15, PH - 0.65 * inch, meta.get("author", ""))
        c.setLineWidth(0.25)
        c.setStrokeColor(MUTED)
        c.line(MARGIN_L, PH - 0.72 * inch, PW - 0.5 * inch, PH - 0.72 * inch)
        # Draw footer
        c.drawCentredString(PW / 2, 0.5 * inch, str(page_num))
        # Flush pending annotations
        ay = PH - MARGIN_T
        for annot in pending_annots:
            label   = annot.get("gbo_ref", "")
            caption = annot.get("label", "")
            text    = f"{label} — {caption}"
            c.setFont(ANNOT_FONT, ANNOT_SIZE)
            c.setFillColor(ANNOT_INK)
            # Wrap annotation text
            wrapped = textwrap.wrap(text, 28)
            block_h = len(wrapped) * ANNOT_LEAD
            entry   = annot.get("connections_entry", "")
            link    = f"connections/connections.pdf#{entry}" if entry else ""
            if link:
                c.linkURL(link,
                          (ANNOT_X, ay - block_h, ANNOT_X + ANNOT_W, ay + ANNOT_SIZE),
                          relative=1)
            for wline in wrapped:
                if ay < MARGIN_B + ANNOT_LEAD:
                    break
                c.drawString(ANNOT_X, ay, wline)
                ay -= ANNOT_LEAD
            ay -= 6  # gap between annotations
        pending_annots.clear()
        c.showPage()
        page_num += 1
        y = PH - MARGIN_T - 0.3 * inch  # below header rule

    # ── Main typesetting loop ─────────────────────────────────────────────
    # Draw page background (ivory) — do first page
    c.setFillColor(PAGE_BG)
    c.rect(0, 0, PW, PH, fill=1, stroke=0)

    y = PH - MARGIN_T - 0.3 * inch  # start below header area

    for line_text, is_para_start in lines:
        if y < MARGIN_B + BODY_LEAD:
            new_page()
            # New page background
            c.setFillColor(PAGE_BG)
            c.rect(0, 0, PW, PH, fill=1, stroke=0)

        c.setFillColor(INK)

        if not line_text:
            y -= BODY_LEAD * 0.5
            continue

        # Check if this line contains an annotated passage
        for key, annot in annot_index.items():
            if key and key[:40] in line_text:
                # Underline this line in gold
                c.setStrokeColor(GOLD)
                c.setLineWidth(0.4)
                lw = pdfmetrics.stringWidth(line_text, BODY_FONT, BODY_SIZE)
                c.line(MARGIN_L, y - 1, MARGIN_L + min(lw, TEXT_W), y - 1)
                pending_annots.append(annot)

        x = MARGIN_L + (18 if is_para_start else 0)
        c.setFont(BODY_FONT, BODY_SIZE)
        c.setFillColor(INK)
        c.drawString(x, y, line_text)
        y -= BODY_LEAD

    new_page()  # flush last page
    c.save()
    print(f"Saved → {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py -3 annotations/build.py <slug>")
        sys.exit(1)
    if sys.argv[1] == "--all":
        for f in ANNOT_DIR.glob("*.yaml"):
            build_book(f.stem)
    else:
        build_book(sys.argv[1])
